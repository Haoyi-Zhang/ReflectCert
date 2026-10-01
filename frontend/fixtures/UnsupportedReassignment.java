final class UnsupportedReassignment {
    void resolve(boolean h) throws Exception {
        String name = "pkg.A";
        if (h) {
            name = "pkg.B";
        }
        java.lang.Class.forName(name);
    }
}
