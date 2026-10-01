final class RuntimeInvoke {
    public static final class A {
        public String run(String value) { return "A.run:" + value; }
        public String stop(String value) { return "A.stop:" + value; }
    }

    public static final class B {
        public String run(String value) { return "B.run:" + value; }
        public String stop(String value) { return "B.stop:" + value; }
    }

    static String reflect(boolean h, boolean k, String value) throws Exception {
        boolean chooseA = h && !k;
        String className = "RuntimeInvoke$".concat(chooseA ? "A" : "B");
        java.lang.Class<?> owner = java.lang.Class.forName(className);
        String memberName = h ? "run" : "stop";
        Object receiver = owner.getConstructor().newInstance();
        java.lang.reflect.Method method = owner.getMethod(memberName, String.class);
        return (String) method.invoke(receiver, value);
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) {
            throw new IllegalArgumentException("expected two Boolean arguments and one value");
        }
        System.out.println(reflect(Boolean.parseBoolean(args[0]), Boolean.parseBoolean(args[1]), args[2]));
    }
}
