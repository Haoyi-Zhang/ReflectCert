final class RuntimeFinite {
    public static final class A {
        public String run(String value) { return value; }
        public String stop(String value) { return value; }
    }

    public static final class B {
        public String run(String value) { return value; }
        public String stop(String value) { return value; }
    }

    static String resolve(boolean h, boolean k) throws Exception {
        boolean chooseA = h && !k;
        String className = "RuntimeFinite$".concat(chooseA ? "A" : "B");
        Class<?> owner = Class.forName(className);
        String memberName = h ? "run" : "stop";
        java.lang.reflect.Method method = owner.getMethod(memberName, String.class);
        return owner.getName() + "\t" + method.getName() + "\t" + method.getParameterTypes()[0].getName();
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            throw new IllegalArgumentException("expected two Boolean arguments");
        }
        System.out.println(resolve(Boolean.parseBoolean(args[0]), Boolean.parseBoolean(args[1])));
    }
}
