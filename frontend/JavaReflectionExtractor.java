import com.sun.source.tree.ArrayAccessTree;
import com.sun.source.tree.AssignmentTree;
import com.sun.source.tree.BinaryTree;
import com.sun.source.tree.BlockTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.ConditionalExpressionTree;
import com.sun.source.tree.DoWhileLoopTree;
import com.sun.source.tree.EnhancedForLoopTree;
import com.sun.source.tree.ForLoopTree;
import com.sun.source.tree.IfTree;
import com.sun.source.tree.ExpressionTree;
import com.sun.source.tree.IdentifierTree;
import com.sun.source.tree.LiteralTree;
import com.sun.source.tree.MemberSelectTree;
import com.sun.source.tree.MethodInvocationTree;
import com.sun.source.tree.MethodTree;
import com.sun.source.tree.NewArrayTree;
import com.sun.source.tree.ParenthesizedTree;
import com.sun.source.tree.PrimitiveTypeTree;
import com.sun.source.tree.Tree;
import com.sun.source.tree.TypeCastTree;
import com.sun.source.tree.WhileLoopTree;
import com.sun.source.tree.UnaryTree;
import com.sun.source.tree.VariableTree;
import com.sun.source.util.JavacTask;
import com.sun.source.util.SourcePositions;
import com.sun.source.util.TreePathScanner;
import com.sun.source.util.TreeScanner;
import com.sun.source.util.Trees;

import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * A deliberately small Java-source bridge for the reflection-certificate model.
 *
 * <p>The extractor uses javac's parser, but not type attribution. It accepts only
 * syntax whose finite string meaning can be reconstructed without Android or
 * application classpaths. Unsupported reflective sites are emitted as explicit
 * rejections rather than guessed.</p>
 */
public final class JavaReflectionExtractor {
    private static final String FORMAT = "rrc-java-front-v1";

    private JavaReflectionExtractor() {}

    private static final class Expr {
        final Map<String, Object> value;
        final String constantString;
        final Boolean constantBoolean;

        Expr(Map<String, Object> value, String constantString, Boolean constantBoolean) {
            this.value = value;
            this.constantString = constantString;
            this.constantBoolean = constantBoolean;
        }

        static Expr litString(String value) {
            Map<String, Object> out = map("op", "lit", "value", value);
            return new Expr(out, value, null);
        }

        static Expr litBoolean(boolean value) {
            Map<String, Object> out = map("op", "lit", "value", value);
            return new Expr(out, null, value);
        }

        static Expr input(String name) {
            Map<String, Object> out = map("op", "input", "name", name);
            return new Expr(out, null, null);
        }

        static Expr unary(String op, Expr arg) {
            Map<String, Object> out = map("op", op, "args", List.of(arg.value));
            Boolean constant = null;
            if (op.equals("not") && arg.constantBoolean != null) {
                constant = !arg.constantBoolean;
            }
            return new Expr(out, null, constant);
        }

        static Expr binary(String op, Expr left, Expr right) {
            Map<String, Object> out = map("op", op, "args", List.of(left.value, right.value));
            if (op.equals("cat")) {
                String constant = left.constantString != null && right.constantString != null
                        ? left.constantString + right.constantString : null;
                return new Expr(out, constant, null);
            }
            Boolean constant = null;
            if (op.equals("and") && left.constantBoolean != null && right.constantBoolean != null) {
                constant = left.constantBoolean && right.constantBoolean;
            } else if (op.equals("or") && left.constantBoolean != null && right.constantBoolean != null) {
                constant = left.constantBoolean || right.constantBoolean;
            } else if (op.equals("eq")) {
                if (left.constantBoolean != null && right.constantBoolean != null) {
                    constant = left.constantBoolean.equals(right.constantBoolean);
                } else if (left.constantString != null && right.constantString != null) {
                    constant = left.constantString.equals(right.constantString);
                }
            }
            return new Expr(out, null, constant);
        }

        static Expr ite(Expr condition, Expr yes, Expr no) {
            Map<String, Object> out = map("op", "ite", "args", List.of(condition.value, yes.value, no.value));
            String constant = null;
            if (condition.constantBoolean != null) {
                constant = condition.constantBoolean ? yes.constantString : no.constantString;
            } else if (yes.constantString != null && yes.constantString.equals(no.constantString)) {
                constant = yes.constantString;
            }
            return new Expr(out, constant, null);
        }
    }

    private record ClassRef(String loader, Expr className) {}

    private static final class Env {
        final Map<String, Expr> strings = new HashMap<>();
        final Map<String, ClassRef> classes = new HashMap<>();
        final Map<String, Expr> booleans = new HashMap<>();
        final Set<String> classTyped = new HashSet<>();
        final Set<String> loaderTyped = new HashSet<>();

        Env copy() {
            Env out = new Env();
            out.strings.putAll(strings);
            out.classes.putAll(classes);
            out.booleans.putAll(booleans);
            out.classTyped.addAll(classTyped);
            out.loaderTyped.addAll(loaderTyped);
            return out;
        }

        void invalidate(Collection<String> names) {
            for (String name : names) {
                strings.remove(name);
                classes.remove(name);
                booleans.remove(name);
            }
        }
    }

    private static Map<String, Object> map(Object... keyValues) {
        LinkedHashMap<String, Object> out = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            out.put((String) keyValues[i], keyValues[i + 1]);
        }
        return out;
    }

    private static final class Scanner extends TreePathScanner<Void, Env> {
        private static final Set<String> CLASS_APIS = Set.of(
                "newInstance", "getConstructor", "getConstructors",
                "getMethod", "getDeclaredMethod", "getMethods", "getDeclaredMethods",
                "getField", "getDeclaredField", "getFields", "getDeclaredFields");

        private final CompilationUnitTree unit;
        private final SourcePositions positions;
        private final List<Map<String, Object>> events = new ArrayList<>();
        private long sequence = 0;
        private int controlDepth = 0;

        Scanner(CompilationUnitTree unit, SourcePositions positions) {
            this.unit = unit;
            this.positions = positions;
        }

        List<Map<String, Object>> events() {
            events.sort(Comparator
                    .comparingLong((Map<String, Object> event) -> ((Number) event.get("offset")).longValue())
                    .thenComparingLong(event -> ((Number) event.get("sequence")).longValue()));
            for (Map<String, Object> event : events) {
                event.remove("sequence");
            }
            return events;
        }

        @Override
        public Void visitMethod(MethodTree node, Env ignored) {
            Env env = new Env();
            for (VariableTree parameter : node.getParameters()) {
                String parameterName = parameter.getName().toString();
                if (isBooleanType(parameter.getType())) {
                    env.booleans.put(parameterName, Expr.input(parameterName));
                }
                if (isClassType(parameter.getType())) {
                    env.classTyped.add(parameterName);
                }
                if (isClassLoaderType(parameter.getType())) {
                    env.loaderTyped.add(parameterName);
                }
            }
            BlockTree body = node.getBody();
            if (body != null) {
                scan(body, env);
            }
            return null;
        }

        @Override
        public Void visitVariable(VariableTree node, Env env) {
            String name = node.getName().toString();
            // A declaration shadows any tracked binding with the same name.
            env.strings.remove(name);
            env.classes.remove(name);
            env.booleans.remove(name);
            env.classTyped.remove(name);
            env.loaderTyped.remove(name);
            if (isClassType(node.getType())) {
                env.classTyped.add(name);
            }
            if (isClassLoaderType(node.getType())) {
                env.loaderTyped.add(name);
            }
            ExpressionTree initializer = node.getInitializer();
            if (initializer != null) {
                scan(initializer, env);
                bind(name, initializer, env);
            }
            return null;
        }

        @Override
        public Void visitAssignment(AssignmentTree node, Env env) {
            scan(node.getExpression(), env);
            ExpressionTree variable = strip(node.getVariable());
            if (variable instanceof IdentifierTree identifier) {
                bind(identifier.getName().toString(), node.getExpression(), env);
            }
            return null;
        }

        @Override
        public Void visitMethodInvocation(MethodInvocationTree node, Env env) {
            // Visit nested receivers/arguments first so source-level chains are emitted
            // from the innermost lookup to the outer use.
            super.visitMethodInvocation(node, env);

            String name = methodName(node);
            ExpressionTree receiver = receiver(node);
            if (controlDepth > 0 && isReflectionCandidate(name, receiver, env)) {
                reject(node, reflectionKind(name), "unsupported_control_context");
                return null;
            }
            if (name.equals("forName") && isClassName(receiver)) {
                Expr className = oneStringArgument(node, env);
                if (className == null) {
                    reject(node, "Class.forName", "unsupported_class_name_expression");
                } else {
                    accept(node, "Class.forName", "default", className,
                            Expr.litString("<class>"), "()", null);
                }
                return null;
            }

            if (name.equals("loadClass")) {
                if (!isApplicationClassLoader(receiver)) {
                    if (isLoaderTypedReceiver(receiver, env)) {
                        reject(node, "ClassLoader.loadClass", "unsupported_loader_receiver");
                    }
                    return null;
                }
                Expr className = oneStringArgument(node, env);
                if (className == null) {
                    reject(node, "ClassLoader.loadClass", "unsupported_class_name_expression");
                } else {
                    accept(node, "ClassLoader.loadClass", "app", className,
                            Expr.litString("<class>"), "()", null);
                }
                return null;
            }

            if (!CLASS_APIS.contains(name)) {
                return null;
            }
            ClassRef owner = resolveClass(receiver, env);
            String kind = "Class." + name;
            if (owner == null) {
                // Constructor.newInstance and unrelated methods with reflection-like
                // names are deliberately outside this lookup frontend. A syntactically
                // class-typed receiver, however, must fail closed.
                if (isClassTypedReceiver(receiver, env)) {
                    reject(node, kind, "unresolved_class_receiver");
                }
                return null;
            }

            switch (name) {
                case "newInstance" -> accept(node, kind, owner.loader(), owner.className(),
                        Expr.litString("<init>"), "()", null);
                case "getConstructor" -> {
                    String signature = signature(node.getArguments(), env);
                    if (signature == null) {
                        reject(node, kind, "unsupported_parameter_type_expression");
                    } else {
                        accept(node, kind, owner.loader(), owner.className(),
                                Expr.litString("<init>"), signature, null);
                    }
                }
                case "getConstructors" -> accept(node, kind, owner.loader(), owner.className(),
                        Expr.litString("<constructors>"), "[]", null);
                case "getMethod", "getDeclaredMethod" -> {
                    if (node.getArguments().isEmpty()) {
                        reject(node, kind, "missing_member_name");
                        return null;
                    }
                    Expr member = stringExpr(node.getArguments().get(0), env);
                    String signature = signature(node.getArguments().subList(1, node.getArguments().size()), env);
                    if (member == null) {
                        reject(node, kind, "unsupported_member_name_expression");
                    } else if (signature == null) {
                        reject(node, kind, "unsupported_parameter_type_expression");
                    } else {
                        accept(node, kind, owner.loader(), owner.className(), member, signature, null);
                    }
                }
                case "getMethods", "getDeclaredMethods" -> accept(node, kind, owner.loader(), owner.className(),
                        Expr.litString("<methods>"), "[]", null);
                case "getField", "getDeclaredField" -> {
                    Expr member = oneStringArgument(node, env);
                    if (member == null) {
                        reject(node, kind, "unsupported_member_name_expression");
                    } else {
                        accept(node, kind, owner.loader(), owner.className(), member, "field", null);
                    }
                }
                case "getFields", "getDeclaredFields" -> accept(node, kind, owner.loader(), owner.className(),
                        Expr.litString("<fields>"), "fields[]", null);
                default -> throw new IllegalStateException(name);
            }
            return null;
        }

        @Override
        public Void visitIf(IfTree node, Env env) {
            scan(node.getCondition(), env);
            scanControlled(node.getThenStatement(), env);
            if (node.getElseStatement() != null) {
                scanControlled(node.getElseStatement(), env);
            }
            env.invalidate(assignedNames(node.getThenStatement()));
            if (node.getElseStatement() != null) {
                env.invalidate(assignedNames(node.getElseStatement()));
            }
            return null;
        }

        @Override
        public Void visitForLoop(ForLoopTree node, Env env) {
            for (var initializer : node.getInitializer()) {
                scan(initializer, env);
            }
            Env local = env.copy();
            controlDepth++;
            try {
                if (node.getCondition() != null) scan(node.getCondition(), local);
                scan(node.getStatement(), local);
                for (var update : node.getUpdate()) scan(update, local);
            } finally {
                controlDepth--;
            }
            env.invalidate(assignedNames(node));
            return null;
        }

        @Override
        public Void visitEnhancedForLoop(EnhancedForLoopTree node, Env env) {
            scan(node.getExpression(), env);
            scanControlled(node.getStatement(), env);
            env.invalidate(assignedNames(node));
            return null;
        }

        @Override
        public Void visitWhileLoop(WhileLoopTree node, Env env) {
            Env local = env.copy();
            controlDepth++;
            try {
                scan(node.getCondition(), local);
                scan(node.getStatement(), local);
            } finally {
                controlDepth--;
            }
            env.invalidate(assignedNames(node));
            return null;
        }

        @Override
        public Void visitDoWhileLoop(DoWhileLoopTree node, Env env) {
            Env local = env.copy();
            controlDepth++;
            try {
                scan(node.getStatement(), local);
                scan(node.getCondition(), local);
            } finally {
                controlDepth--;
            }
            env.invalidate(assignedNames(node));
            return null;
        }

        private void scanControlled(Tree tree, Env env) {
            controlDepth++;
            try {
                scan(tree, env.copy());
            } finally {
                controlDepth--;
            }
        }

        private Set<String> assignedNames(Tree tree) {
            Set<String> names = new HashSet<>();
            new TreeScanner<Void, Void>() {
                @Override
                public Void visitAssignment(AssignmentTree assignment, Void ignored) {
                    ExpressionTree variable = strip(assignment.getVariable());
                    if (variable instanceof IdentifierTree identifier) {
                        names.add(identifier.getName().toString());
                    }
                    return super.visitAssignment(assignment, ignored);
                }
            }.scan(tree, null);
            return names;
        }

        private boolean isReflectionCandidate(String name, ExpressionTree receiver, Env env) {
            if (name.equals("forName")) {
                return isClassName(receiver);
            }
            if (name.equals("loadClass")) {
                return isApplicationClassLoader(receiver) || isLoaderTypedReceiver(receiver, env);
            }
            if (CLASS_APIS.contains(name)) {
                return resolveClass(receiver, env) != null || isClassTypedReceiver(receiver, env);
            }
            return false;
        }

        private boolean isClassTypedReceiver(ExpressionTree receiver, Env env) {
            if (receiver == null) {
                return false;
            }
            ExpressionTree expression = strip(receiver);
            if (expression instanceof IdentifierTree identifier) {
                return env.classTyped.contains(identifier.getName().toString());
            }
            if (expression instanceof MethodInvocationTree invocation) {
                return methodName(invocation).equals("getClass") && invocation.getArguments().isEmpty();
            }
            return false;
        }

        private boolean isLoaderTypedReceiver(ExpressionTree receiver, Env env) {
            if (receiver == null) {
                return false;
            }
            ExpressionTree expression = strip(receiver);
            return expression instanceof IdentifierTree identifier
                    && env.loaderTyped.contains(identifier.getName().toString());
        }

        private String reflectionKind(String name) {
            if (name.equals("forName")) return "Class.forName";
            if (name.equals("loadClass")) return "ClassLoader.loadClass";
            return "Class." + name;
        }

        private void bind(String name, ExpressionTree expression, Env env) {
            Expr string = stringExpr(expression, env);
            if (string != null) {
                env.strings.put(name, string);
            } else {
                env.strings.remove(name);
            }
            ClassRef classRef = resolveClass(expression, env);
            if (classRef != null) {
                env.classes.put(name, classRef);
            } else {
                env.classes.remove(name);
            }
            Expr booleanValue = booleanExpr(expression, env);
            if (booleanValue != null) {
                env.booleans.put(name, booleanValue);
            } else {
                env.booleans.remove(name);
            }
        }

        private void accept(Tree node, String kind, String loader, Expr className,
                            Expr member, String signature, String note) {
            LinkedHashMap<String, Object> event = position(node);
            event.put("status", "accepted");
            event.put("kind", kind);
            event.put("loader", loader);
            event.put("class_expr", className.value);
            event.put("class_constant", className.constantString);
            event.put("member_expr", member.value);
            event.put("member_constant", member.constantString);
            event.put("signature", signature);
            if (note != null) {
                event.put("note", note);
            }
            events.add(event);
        }

        private void reject(Tree node, String kind, String reason) {
            LinkedHashMap<String, Object> event = position(node);
            event.put("status", "rejected");
            event.put("kind", kind);
            event.put("reason", reason);
            events.add(event);
        }

        private LinkedHashMap<String, Object> position(Tree node) {
            long offset = positions.getStartPosition(unit, node);
            long end = positions.getEndPosition(unit, node);
            long line = offset >= 0 ? unit.getLineMap().getLineNumber(offset) : -1;
            long column = offset >= 0 ? unit.getLineMap().getColumnNumber(offset) : -1;
            LinkedHashMap<String, Object> event = new LinkedHashMap<>();
            event.put("offset", offset);
            event.put("end_offset", end);
            event.put("line", line);
            event.put("column", column);
            event.put("sequence", sequence++);
            return event;
        }

        private Expr oneStringArgument(MethodInvocationTree node, Env env) {
            if (node.getArguments().size() != 1) {
                return null;
            }
            return stringExpr(node.getArguments().get(0), env);
        }

        private Expr stringExpr(ExpressionTree input, Env env) {
            ExpressionTree expression = strip(input);
            if (expression instanceof LiteralTree literal && literal.getValue() instanceof String text) {
                return Expr.litString(text);
            }
            if (expression instanceof IdentifierTree identifier) {
                return env.strings.get(identifier.getName().toString());
            }
            if (expression instanceof BinaryTree binary && binary.getKind() == Tree.Kind.PLUS) {
                Expr left = stringExpr(binary.getLeftOperand(), env);
                Expr right = stringExpr(binary.getRightOperand(), env);
                return left != null && right != null ? Expr.binary("cat", left, right) : null;
            }
            if (expression instanceof ConditionalExpressionTree conditional) {
                Expr condition = booleanExpr(conditional.getCondition(), env);
                Expr yes = stringExpr(conditional.getTrueExpression(), env);
                Expr no = stringExpr(conditional.getFalseExpression(), env);
                return condition != null && yes != null && no != null ? Expr.ite(condition, yes, no) : null;
            }
            if (expression instanceof MethodInvocationTree invocation
                    && methodName(invocation).equals("concat")
                    && invocation.getArguments().size() == 1) {
                Expr left = stringExpr(receiver(invocation), env);
                Expr right = stringExpr(invocation.getArguments().get(0), env);
                return left != null && right != null ? Expr.binary("cat", left, right) : null;
            }
            return null;
        }

        private Expr booleanExpr(ExpressionTree input, Env env) {
            ExpressionTree expression = strip(input);
            if (expression instanceof LiteralTree literal && literal.getValue() instanceof Boolean value) {
                return Expr.litBoolean(value);
            }
            if (expression instanceof IdentifierTree identifier) {
                String name = identifier.getName().toString();
                return env.booleans.get(name);
            }
            if (expression instanceof UnaryTree unary && unary.getKind() == Tree.Kind.LOGICAL_COMPLEMENT) {
                Expr arg = booleanExpr(unary.getExpression(), env);
                return arg == null ? null : Expr.unary("not", arg);
            }
            if (expression instanceof BinaryTree binary) {
                String op = switch (binary.getKind()) {
                    case CONDITIONAL_AND -> "and";
                    case CONDITIONAL_OR -> "or";
                    case EQUAL_TO -> "eq";
                    default -> null;
                };
                if (op == null) {
                    return null;
                }
                Expr left = booleanExpr(binary.getLeftOperand(), env);
                Expr right = booleanExpr(binary.getRightOperand(), env);
                if (left != null && right != null) {
                    return Expr.binary(op, left, right);
                }
                if (op.equals("eq")) {
                    Expr leftString = stringExpr(binary.getLeftOperand(), env);
                    Expr rightString = stringExpr(binary.getRightOperand(), env);
                    if (leftString != null && rightString != null) {
                        return Expr.binary(op, leftString, rightString);
                    }
                }
            }
            return null;
        }

        private ClassRef resolveClass(ExpressionTree input, Env env) {
            if (input == null) {
                return null;
            }
            ExpressionTree expression = strip(input);
            if (expression instanceof IdentifierTree identifier) {
                return env.classes.get(identifier.getName().toString());
            }
            if (expression instanceof MethodInvocationTree invocation) {
                String name = methodName(invocation);
                ExpressionTree receiver = receiver(invocation);
                if (name.equals("forName") && isClassName(receiver)) {
                    Expr className = oneStringArgument(invocation, env);
                    return className == null ? null : new ClassRef("default", className);
                }
                if (name.equals("loadClass") && isApplicationClassLoader(receiver)) {
                    Expr className = oneStringArgument(invocation, env);
                    return className == null ? null : new ClassRef("app", className);
                }
            }
            return null;
        }

        private String signature(List<? extends ExpressionTree> arguments, Env env) {
            List<ExpressionTree> flattened = new ArrayList<>();
            if (arguments.size() == 1 && arguments.get(0) instanceof NewArrayTree array) {
                if (isEmptyArray(array)) {
                    return "()";
                }
                if (array.getInitializers() == null) {
                    return null;
                }
                flattened.addAll(array.getInitializers());
            } else {
                flattened.addAll(arguments);
            }
            List<String> types = new ArrayList<>();
            for (ExpressionTree argument : flattened) {
                String type = classLiteral(argument);
                if (type == null) {
                    return null;
                }
                types.add(type);
            }
            return "(" + String.join(",", types) + ")";
        }

        private boolean isEmptyArray(NewArrayTree array) {
            if (array.getInitializers() != null) {
                return array.getInitializers().isEmpty();
            }
            return array.getDimensions().size() == 1
                    && array.getDimensions().get(0) instanceof LiteralTree literal
                    && Integer.valueOf(0).equals(literal.getValue());
        }

        private String classLiteral(ExpressionTree input) {
            ExpressionTree expression = strip(input);
            if (expression instanceof MemberSelectTree select
                    && select.getIdentifier().contentEquals("class")) {
                return simpleType(select.getExpression().toString());
            }
            return null;
        }

        private String simpleType(String type) {
            int generic = type.indexOf('<');
            if (generic >= 0) {
                type = type.substring(0, generic);
            }
            int dot = type.lastIndexOf('.');
            return dot >= 0 ? type.substring(dot + 1) : type;
        }

        private boolean isClassName(ExpressionTree receiver) {
            if (receiver == null) {
                return false;
            }
            String text = receiver.toString();
            return text.equals("Class") || text.equals("java.lang.Class");
        }

        private boolean isApplicationClassLoader(ExpressionTree receiver) {
            if (!(strip(receiver) instanceof MethodInvocationTree invocation)) {
                return false;
            }
            return methodName(invocation).equals("getClassLoader") && invocation.getArguments().isEmpty();
        }

        private String methodName(MethodInvocationTree node) {
            ExpressionTree select = node.getMethodSelect();
            if (select instanceof MemberSelectTree member) {
                return member.getIdentifier().toString();
            }
            if (select instanceof IdentifierTree identifier) {
                return identifier.getName().toString();
            }
            return select.toString();
        }

        private ExpressionTree receiver(MethodInvocationTree node) {
            ExpressionTree select = node.getMethodSelect();
            return select instanceof MemberSelectTree member ? member.getExpression() : null;
        }

        private ExpressionTree strip(ExpressionTree input) {
            ExpressionTree current = input;
            while (current instanceof ParenthesizedTree parenthesized
                    || current instanceof TypeCastTree) {
                if (current instanceof ParenthesizedTree parenthesized) {
                    current = parenthesized.getExpression();
                } else {
                    current = ((TypeCastTree) current).getExpression();
                }
            }
            return current;
        }

        private boolean isClassType(Tree type) {
            if (type == null) return false;
            String text = type.toString();
            return text.equals("Class") || text.startsWith("Class<")
                    || text.equals("java.lang.Class") || text.startsWith("java.lang.Class<");
        }

        private boolean isClassLoaderType(Tree type) {
            if (type == null) return false;
            String text = type.toString();
            return text.equals("ClassLoader") || text.equals("java.lang.ClassLoader");
        }

        private boolean isBooleanType(Tree type) {
            return type instanceof PrimitiveTypeTree primitive
                    && primitive.getPrimitiveTypeKind().name().equals("BOOLEAN");
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.err.println("usage: JavaReflectionExtractor <source.java> ...");
            System.exit(2);
        }
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException("a full JDK is required");
        }
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        List<Path> paths = new ArrayList<>();
        for (String arg : args) {
            paths.add(Path.of(arg));
        }
        List<Map<String, Object>> filesOut = new ArrayList<>();
        try (StandardJavaFileManager manager = compiler.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            Iterable<? extends JavaFileObject> inputs = manager.getJavaFileObjectsFromPaths(paths);
            JavacTask task = (JavacTask) compiler.getTask(
                    null, manager, diagnostics, List.of("-proc:none"), null, inputs);
            Iterable<? extends CompilationUnitTree> units = task.parse();
            Trees trees = Trees.instance(task);
            SourcePositions positions = trees.getSourcePositions();
            for (CompilationUnitTree unit : units) {
                Scanner scanner = new Scanner(unit, positions);
                scanner.scan(unit, new Env());
                LinkedHashMap<String, Object> file = new LinkedHashMap<>();
                file.put("path", Path.of(unit.getSourceFile().toUri()).toString());
                file.put("package", unit.getPackageName() == null ? "" : unit.getPackageName().toString());
                file.put("events", scanner.events());
                filesOut.add(file);
            }
        }
        List<Map<String, Object>> errors = new ArrayList<>();
        for (Diagnostic<? extends JavaFileObject> diagnostic : diagnostics.getDiagnostics()) {
            if (diagnostic.getKind() == Diagnostic.Kind.ERROR) {
                LinkedHashMap<String, Object> error = new LinkedHashMap<>();
                error.put("path", diagnostic.getSource() == null ? "" : Path.of(diagnostic.getSource().toUri()).toString());
                error.put("line", diagnostic.getLineNumber());
                error.put("column", diagnostic.getColumnNumber());
                error.put("message", diagnostic.getMessage(Locale.ROOT));
                errors.add(error);
            }
        }
        filesOut.sort(Comparator.comparing(file -> file.get("path").toString()));
        LinkedHashMap<String, Object> output = new LinkedHashMap<>();
        output.put("format", FORMAT);
        output.put("files", filesOut);
        output.put("parse_errors", errors);
        System.out.println(json(output));
        if (!errors.isEmpty()) {
            System.exit(1);
        }
    }

    private static String json(Object value) {
        StringBuilder out = new StringBuilder();
        appendJson(out, value);
        return out.toString();
    }

    private static void appendJson(StringBuilder out, Object value) {
        if (value == null) {
            out.append("null");
        } else if (value instanceof String text) {
            out.append('"');
            for (int i = 0; i < text.length(); i++) {
                char ch = text.charAt(i);
                switch (ch) {
                    case '"' -> out.append("\\\"");
                    case '\\' -> out.append("\\\\");
                    case '\b' -> out.append("\\b");
                    case '\f' -> out.append("\\f");
                    case '\n' -> out.append("\\n");
                    case '\r' -> out.append("\\r");
                    case '\t' -> out.append("\\t");
                    default -> {
                        if (ch < 0x20) {
                            out.append(String.format("\\u%04x", (int) ch));
                        } else {
                            out.append(ch);
                        }
                    }
                }
            }
            out.append('"');
        } else if (value instanceof Boolean || value instanceof Number) {
            out.append(value);
        } else if (value instanceof Map<?, ?> map) {
            out.append('{');
            boolean first = true;
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (!first) out.append(',');
                first = false;
                appendJson(out, entry.getKey().toString());
                out.append(':');
                appendJson(out, entry.getValue());
            }
            out.append('}');
        } else if (value instanceof Collection<?> collection) {
            out.append('[');
            boolean first = true;
            for (Object element : collection) {
                if (!first) out.append(',');
                first = false;
                appendJson(out, element);
            }
            out.append(']');
        } else {
            throw new IllegalArgumentException("cannot encode " + value.getClass());
        }
    }
}
