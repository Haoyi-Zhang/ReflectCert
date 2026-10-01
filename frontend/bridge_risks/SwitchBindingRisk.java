final class SwitchBindingRisk {
    static final class A {}
    static final class B {}

    static String run(boolean h) throws Exception {
        String name = "SwitchBindingRisk$A";
        switch (h ? 0 : 1) {
            case 0:
                name = "SwitchBindingRisk$A";
                break;
            default:
                name = "SwitchBindingRisk$B";
        }
        return java.lang.Class.forName(name).getSimpleName();
    }

    public static void main(String[] args) throws Exception {
        System.out.println(run(Boolean.parseBoolean(args[0])));
    }
}
