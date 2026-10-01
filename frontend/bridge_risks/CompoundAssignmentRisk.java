final class CompoundAssignmentRisk {
    static final class A {}
    static final class B {}

    static String stringCase(boolean h) throws Exception {
        String name = "CompoundAssignmentRisk$";
        name += h ? "A" : "B";
        return java.lang.Class.forName(name).getSimpleName();
    }

    static String booleanCase(boolean h, boolean k) throws Exception {
        boolean chooseA = h;
        chooseA &= k;
        String name = "CompoundAssignmentRisk$" + (chooseA ? "A" : "B");
        return java.lang.Class.forName(name).getSimpleName();
    }

    public static void main(String[] args) throws Exception {
        boolean h = Boolean.parseBoolean(args[0]);
        boolean k = Boolean.parseBoolean(args[1]);
        System.out.println(stringCase(h) + "\t" + booleanCase(h, k));
    }
}
