final class UnsupportedControl {
    void resolve(boolean h) throws Exception {
        if (h) {
            Class.forName("pkg.A");
        }
    }
}
