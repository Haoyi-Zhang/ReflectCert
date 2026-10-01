final class UnsupportedControl {
    void resolve(boolean h) throws Exception {
        if (h) {
            java.lang.Class.forName("pkg.A");
        }
    }
}
