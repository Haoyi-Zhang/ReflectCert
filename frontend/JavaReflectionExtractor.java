import com.sun.source.tree.ArrayAccessTree;
import com.sun.source.tree.AssignmentTree;
import com.sun.source.tree.BinaryTree;
import com.sun.source.tree.BlockTree;
import com.sun.source.tree.CaseTree;
import com.sun.source.tree.ClassTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.CompoundAssignmentTree;
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
import com.sun.source.tree.SwitchExpressionTree;
import com.sun.source.tree.SwitchTree;
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
    private static final String SIMPLE_CLASS_ASSUMPTION =
            "pinned-source audit: simple Class resolves to java.lang.Class";
    private static final String APPLICATION_LOADER_ASSUMPTION =
            "pinned-source audit: this.getClassLoader resolves to the application loader";

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

    private record Policy(boolean auditSimpleJavaLangClass,
                          boolean auditThisApplicationLoader) {}

    private record ClassRef(String loader, Expr className, List<String> assumptions) {}

    private record ApiDecision(boolean accepted, String rejection,
                               String loader, List<String> assumptions) {
        static ApiDecision accepted(String loader, List<String> assumptions) {
            return new ApiDecision(true, null, loader, List.copyOf(assumptions));
        }

        static ApiDecision rejected(String reason) {
            return new ApiDecision(false, reason, null, List.of());
        }

        static ApiDecision absent() {
            return new ApiDecision(false, null, null, List.of());
        }
    }

    private static final class Env {
        final Map<String, Expr> strings = new HashMap<>();
        final Map<String, ClassRef> classes = new HashMap<>();
        final Map<String, Expr> booleans = new HashMap<>();
        final Map<String, String> unsupported = new HashMap<>();
        final Set<String> classTyped = new HashSet<>();
        final Set<String> unauditedClassTyped = new HashSet<>();
        final Set<String> loaderTyped = new HashSet<>();

        Env copy() {
            Env out = new Env();
            out.strings.putAll(strings);
            out.classes.putAll(classes);
            out.booleans.putAll(booleans);
            out.unsupported.putAll(unsupported);
            out.classTyped.addAll(classTyped);
            out.unauditedClassTyped.addAll(unauditedClassTyped);
            out.loaderTyped.addAll(loaderTyped);
            return out;
        }

        void invalidate(Collection<String> names, String reason) {
            for (String name : names) {
                strings.remove(name);
                classes.remove(name);
                booleans.remove(name);
                unsupported.put(name, reason);
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
        private final Policy policy;
        private final boolean simpleClassShadowed;
        private final boolean declaresGetClassLoader;
        private final List<Map<String, Object>> events = new ArrayList<>();
        private long sequence = 0;
        private int controlDepth = 0;

        Scanner(CompilationUnitTree unit, SourcePositions positions, Policy policy) {
            this.unit = unit;
            this.positions = positions;
            this.policy = policy;
            this.simpleClassShadowed = declaresName(unit, "Class");
            this.declaresGetClassLoader = declaresMethod(unit, "getClassLoader");
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
                if (isAcceptedClassType(parameter.getType())) {
                    env.classTyped.add(parameterName);
                } else if (isSimpleClassType(parameter.getType())) {
                    env.unauditedClassTyped.add(parameterName);
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
            env.unsupported.remove(name);
            env.classTyped.remove(name);
            env.unauditedClassTyped.remove(name);
            env.loaderTyped.remove(name);
            if (isAcceptedClassType(node.getType())) {
                env.classTyped.add(name);
            } else if (isSimpleClassType(node.getType())) {
                env.unauditedClassTyped.add(name);
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
        public Void visitCompoundAssignment(CompoundAssignmentTree node, Env env) {
            scan(node.getExpression(), env);
            ExpressionTree variable = strip(node.getVariable());
            if (variable instanceof IdentifierTree identifier) {
                env.invalidate(List.of(identifier.getName().toString()),
                        "unsupported_compound_assignment");
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
            if (name.equals("forName") && looksLikeClassName(receiver)) {
                ApiDecision identity = classApiIdentity(receiver);
                if (!identity.accepted()) {
                    reject(node, "Class.forName", identity.rejection());
                    return null;
                }
                Expr className = oneStringArgument(node, env);
                if (className == null) {
                    reject(node, "Class.forName", failureReason(
                            node.getArguments().isEmpty() ? null : node.getArguments().get(0), env,
                            "unsupported_class_name_expression"));
                } else {
                    accept(node, "Class.forName", "default", className,
                            Expr.litString("<class>"), "()", null, identity.assumptions());
                }
                return null;
            }

            if (name.equals("loadClass")) {
                ApiDecision identity = loaderApiIdentity(receiver, env);
                if (identity.rejection() != null) {
                    reject(node, "ClassLoader.loadClass", identity.rejection());
                    return null;
                }
                if (!identity.accepted()) {
                    return null;
                }
                Expr className = oneStringArgument(node, env);
                if (className == null) {
                    reject(node, "ClassLoader.loadClass", failureReason(
                            node.getArguments().isEmpty() ? null : node.getArguments().get(0), env,
                            "unsupported_class_name_expression"));
                } else {
                    accept(node, "ClassLoader.loadClass", identity.loader(), className,
                            Expr.litString("<class>"), "()", null, identity.assumptions());
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
                } else if (isUnauditedClassTypedReceiver(receiver, env)) {
                    reject(node, kind, "unaudited_class_receiver");
                }
                return null;
            }

            switch (name) {
                case "newInstance" -> accept(node, kind, owner.loader(), owner.className(),
                        Expr.litString("<init>"), "()", null, owner.assumptions());
                case "getConstructor" -> {
                    String signature = signature(node.getArguments(), env);
                    if (signature == null) {
                        reject(node, kind, "unsupported_parameter_type_expression");
                    } else {
                        accept(node, kind, owner.loader(), owner.className(),
                                Expr.litString("<init>"), signature, null, owner.assumptions());
                    }
                }
                case "getConstructors" -> accept(node, kind, owner.loader(), owner.className(),
                        Expr.litString("<constructors>"), "[]", null, owner.assumptions());
                case "getMethod", "getDeclaredMethod" -> {
                    if (node.getArguments().isEmpty()) {
                        reject(node, kind, "missing_member_name");
                        return null;
                    }
                    Expr member = stringExpr(node.getArguments().get(0), env);
                    String signature = signature(node.getArguments().subList(1, node.getArguments().size()), env);
                    if (member == null) {
                        reject(node, kind, failureReason(node.getArguments().get(0), env,
                                "unsupported_member_name_expression"));
                    } else if (signature == null) {
                        reject(node, kind, "unsupported_parameter_type_expression");
                    } else {
                        accept(node, kind, owner.loader(), owner.className(), member, signature,
                                null, owner.assumptions());
                    }
                }
                case "getMethods", "getDeclaredMethods" -> accept(node, kind, owner.loader(), owner.className(),
                        Expr.litString("<methods>"), "[]", null, owner.assumptions());
                case "getField", "getDeclaredField" -> {
                    Expr member = oneStringArgument(node, env);
                    if (member == null) {
                        reject(node, kind, failureReason(
                                node.getArguments().isEmpty() ? null : node.getArguments().get(0), env,
                                "unsupported_member_name_expression"));
                    } else {
                        accept(node, kind, owner.loader(), owner.className(), member, "field",
                                null, owner.assumptions());
                    }
                }
                case "getFields", "getDeclaredFields" -> accept(node, kind, owner.loader(), owner.className(),
                        Expr.litString("<fields>"), "fields[]", null, owner.assumptions());
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
            env.invalidate(assignedNames(node.getThenStatement()), "unsupported_control_state_merge");
            if (node.getElseStatement() != null) {
                env.invalidate(assignedNames(node.getElseStatement()), "unsupported_control_state_merge");
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
            env.invalidate(assignedNames(node), "unsupported_loop_state_merge");
            return null;
        }

        @Override
        public Void visitEnhancedForLoop(EnhancedForLoopTree node, Env env) {
            scan(node.getExpression(), env);
            scanControlled(node.getStatement(), env);
            env.invalidate(assignedNames(node), "unsupported_loop_state_merge");
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
            env.invalidate(assignedNames(node), "unsupported_loop_state_merge");
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
            env.invalidate(assignedNames(node), "unsupported_loop_state_merge");
            return null;
        }

        @Override
        public Void visitSwitch(SwitchTree node, Env env) {
            scan(node.getExpression(), env);
            for (CaseTree branch : node.getCases()) {
                scanControlled(branch, env);
            }
            env.invalidate(assignedNames(node), "unsupported_switch_state_merge");
            return null;
        }

        @Override
        public Void visitSwitchExpression(SwitchExpressionTree node, Env env) {
            scan(node.getExpression(), env);
            for (CaseTree branch : node.getCases()) {
                scanControlled(branch, env);
            }
            env.invalidate(assignedNames(node), "unsupported_switch_state_merge");
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

                @Override
                public Void visitCompoundAssignment(CompoundAssignmentTree assignment, Void ignored) {
                    ExpressionTree variable = strip(assignment.getVariable());
                    if (variable instanceof IdentifierTree identifier) {
                        names.add(identifier.getName().toString());
                    }
                    return super.visitCompoundAssignment(assignment, ignored);
                }
            }.scan(tree, null);
            return names;
        }

        private boolean isReflectionCandidate(String name, ExpressionTree receiver, Env env) {
            if (name.equals("forName")) {
                return looksLikeClassName(receiver);
            }
            if (name.equals("loadClass")) {
                ApiDecision identity = loaderApiIdentity(receiver, env);
                return identity.accepted() || identity.rejection() != null;
            }
            if (CLASS_APIS.contains(name)) {
                return resolveClass(receiver, env) != null || isClassTypedReceiver(receiver, env)
                        || isUnauditedClassTypedReceiver(receiver, env);
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

        private boolean isUnauditedClassTypedReceiver(ExpressionTree receiver, Env env) {
            if (receiver == null) {
                return false;
            }
            ExpressionTree expression = strip(receiver);
            return expression instanceof IdentifierTree identifier
                    && env.unauditedClassTyped.contains(identifier.getName().toString());
        }

        private boolean isLoaderTypedReceiver(ExpressionTree receiver, Env env) {
            if (receiver == null) {
                return false;
            }
            ExpressionTree expression = strip(receiver);
            return expression instanceof IdentifierTree identifier
                    && env.loaderTyped.contains(identifier.getName().toString());
        }

        private boolean looksLikeClassName(ExpressionTree receiver) {
            if (receiver == null) {
                return false;
            }
            String text = receiver.toString();
            return text.equals("Class") || text.equals("java.lang.Class");
        }

        private ApiDecision classApiIdentity(ExpressionTree receiver) {
            if (receiver == null) {
                return ApiDecision.absent();
            }
            String text = receiver.toString();
            if (text.equals("java.lang.Class")) {
                return ApiDecision.accepted("default", List.of());
            }
            if (!text.equals("Class")) {
                return ApiDecision.absent();
            }
            if (simpleClassShadowed) {
                return ApiDecision.rejected("shadowed_class_api_receiver");
            }
            if (!policy.auditSimpleJavaLangClass()) {
                return ApiDecision.rejected("unaudited_class_api_receiver");
            }
            return ApiDecision.accepted("default", List.of(SIMPLE_CLASS_ASSUMPTION));
        }

        private ApiDecision loaderApiIdentity(ExpressionTree receiver, Env env) {
            if (receiver == null) {
                return ApiDecision.absent();
            }
            ExpressionTree expression = strip(receiver);
            if (expression instanceof IdentifierTree && isLoaderTypedReceiver(expression, env)) {
                return ApiDecision.rejected("unsupported_loader_receiver");
            }
            if (!(expression instanceof MethodInvocationTree getter)
                    || !methodName(getter).equals("getClassLoader")
                    || !getter.getArguments().isEmpty()) {
                return ApiDecision.absent();
            }
            ExpressionTree getterReceiver = receiver(getter);
            boolean thisGetter = getterReceiver == null
                    || (strip(getterReceiver) instanceof IdentifierTree identifier
                    && identifier.getName().contentEquals("this"));
            if (!thisGetter) {
                return ApiDecision.rejected("unaudited_loader_getter");
            }
            if (declaresGetClassLoader) {
                return ApiDecision.rejected("shadowed_application_loader_getter");
            }
            if (!policy.auditThisApplicationLoader()) {
                return ApiDecision.rejected("unaudited_loader_getter");
            }
            return ApiDecision.accepted("app", List.of(APPLICATION_LOADER_ASSUMPTION));
        }

        private String reflectionKind(String name) {
            if (name.equals("forName")) return "Class.forName";
            if (name.equals("loadClass")) return "ClassLoader.loadClass";
            return "Class." + name;
        }

        private void bind(String name, ExpressionTree expression, Env env) {
            env.unsupported.remove(name);
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
            if (string == null && classRef == null && booleanValue == null) {
                String reason = failureReason(expression, env, null);
                if (reason != null) {
                    env.unsupported.put(name, reason);
                }
            }
        }

        private void accept(Tree node, String kind, String loader, Expr className,
                            Expr member, String signature, String note,
                            List<String> assumptions) {
            LinkedHashMap<String, Object> event = position(node);
            event.put("status", "accepted");
            event.put("kind", kind);
            event.put("loader", loader);
            event.put("class_expr", className.value);
            event.put("class_constant", className.constantString);
            event.put("member_expr", member.value);
            event.put("member_constant", member.constantString);
            event.put("signature", signature);
            event.put("assumptions", List.copyOf(assumptions));
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

        private String failureReason(ExpressionTree input, Env env, String fallback) {
            if (input == null) {
                return fallback;
            }
            ExpressionTree expression = strip(input);
            if (expression instanceof IdentifierTree identifier) {
                return env.unsupported.getOrDefault(identifier.getName().toString(), fallback);
            }
            if (expression instanceof BinaryTree binary) {
                if (binary.getKind() == Tree.Kind.EQUAL_TO
                        && stringExpr(binary.getLeftOperand(), env) != null
                        && stringExpr(binary.getRightOperand(), env) != null) {
                    return "unsupported_string_reference_equality";
                }
                String left = failureReason(binary.getLeftOperand(), env, null);
                if (left != null) return left;
                String right = failureReason(binary.getRightOperand(), env, null);
                return right != null ? right : fallback;
            }
            if (expression instanceof ConditionalExpressionTree conditional) {
                String condition = failureReason(conditional.getCondition(), env, null);
                if (condition != null) return condition;
                String yes = failureReason(conditional.getTrueExpression(), env, null);
                if (yes != null) return yes;
                String no = failureReason(conditional.getFalseExpression(), env, null);
                return no != null ? no : fallback;
            }
            if (expression instanceof MethodInvocationTree invocation) {
                ExpressionTree invocationReceiver = receiver(invocation);
                if (invocationReceiver != null) {
                    String receiverReason = failureReason(invocationReceiver, env, null);
                    if (receiverReason != null) return receiverReason;
                }
                for (ExpressionTree argument : invocation.getArguments()) {
                    String argumentReason = failureReason(argument, env, null);
                    if (argumentReason != null) return argumentReason;
                }
            }
            return fallback;
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
                if (name.equals("forName") && looksLikeClassName(receiver)) {
                    ApiDecision identity = classApiIdentity(receiver);
                    if (!identity.accepted()) {
                        return null;
                    }
                    Expr className = oneStringArgument(invocation, env);
                    return className == null ? null
                            : new ClassRef("default", className, identity.assumptions());
                }
                if (name.equals("loadClass")) {
                    ApiDecision identity = loaderApiIdentity(receiver, env);
                    if (!identity.accepted()) {
                        return null;
                    }
                    Expr className = oneStringArgument(invocation, env);
                    return className == null ? null
                            : new ClassRef(identity.loader(), className, identity.assumptions());
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

        private boolean isAcceptedClassType(Tree type) {
            if (type == null) return false;
            String text = type.toString();
            if (text.equals("java.lang.Class") || text.startsWith("java.lang.Class<")) {
                return true;
            }
            return isSimpleClassType(type) && policy.auditSimpleJavaLangClass() && !simpleClassShadowed;
        }

        private boolean isSimpleClassType(Tree type) {
            if (type == null) return false;
            String text = type.toString();
            return text.equals("Class") || text.startsWith("Class<");
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

        private static boolean declaresName(CompilationUnitTree unit, String sought) {
            for (var importTree : unit.getImports()) {
                if (!importTree.isStatic()) {
                    String imported = importTree.getQualifiedIdentifier().toString();
                    if (imported.endsWith("." + sought) && !imported.equals("java.lang." + sought)) {
                        return true;
                    }
                }
            }
            final boolean[] found = {false};
            new TreeScanner<Void, Void>() {
                @Override
                public Void visitClass(ClassTree node, Void ignored) {
                    if (node.getSimpleName().contentEquals(sought)) found[0] = true;
                    return super.visitClass(node, ignored);
                }

                @Override
                public Void visitVariable(VariableTree node, Void ignored) {
                    if (node.getName().contentEquals(sought)) found[0] = true;
                    return super.visitVariable(node, ignored);
                }
            }.scan(unit, null);
            return found[0];
        }

        private static boolean declaresMethod(CompilationUnitTree unit, String sought) {
            final boolean[] found = {false};
            new TreeScanner<Void, Void>() {
                @Override
                public Void visitMethod(MethodTree node, Void ignored) {
                    if (node.getName().contentEquals(sought)) found[0] = true;
                    return super.visitMethod(node, ignored);
                }
            }.scan(unit, null);
            return found[0];
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.err.println("usage: JavaReflectionExtractor "
                    + "[--audit-simple-java-lang-class] [--audit-this-application-loader] "
                    + "<source.java> ...");
            System.exit(2);
        }
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException("a full JDK is required");
        }
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        List<Path> paths = new ArrayList<>();
        boolean auditSimpleJavaLangClass = false;
        boolean auditThisApplicationLoader = false;
        for (String arg : args) {
            switch (arg) {
                case "--audit-simple-java-lang-class" -> auditSimpleJavaLangClass = true;
                case "--audit-this-application-loader" -> auditThisApplicationLoader = true;
                default -> paths.add(Path.of(arg));
            }
        }
        if (paths.isEmpty()) {
            throw new IllegalArgumentException("no Java source paths supplied");
        }
        Policy policy = new Policy(auditSimpleJavaLangClass, auditThisApplicationLoader);
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
                Scanner scanner = new Scanner(unit, positions, policy);
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
        output.put("policy", map(
                "audit_simple_java_lang_class", policy.auditSimpleJavaLangClass(),
                "audit_this_application_loader", policy.auditThisApplicationLoader()));
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
