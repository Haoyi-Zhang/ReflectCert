final class UnsupportedLoader {
    void resolve(ClassLoader loader) throws Exception {
        loader.loadClass("pkg.A");
    }
}
