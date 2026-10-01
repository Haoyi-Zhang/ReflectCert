final class UnsupportedHeap {
    void resolve() throws Exception {
        String name = new StringBuilder().append("pkg.A").toString();
        java.lang.Class.forName(name);
    }
}
