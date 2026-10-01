final class ReferenceEqualityRisk {
    static final class ContentEqual {}
    static final class ReferenceDifferent {}

    static String run(boolean h) throws Exception {
        String s = (h ? "a" : "b") + "c";
        String expected = h ? "ac" : "bc";
        boolean sameReference = s == expected;
        java.lang.Class<?> owner = java.lang.Class.forName(
                "ReferenceEqualityRisk$" +
                        (sameReference ? "ContentEqual" : "ReferenceDifferent"));
        return sameReference + "\t" + s.equals(expected) + "\t" + owner.getSimpleName();
    }

    public static void main(String[] args) throws Exception {
        System.out.println(run(Boolean.parseBoolean(args[0])));
    }
}
