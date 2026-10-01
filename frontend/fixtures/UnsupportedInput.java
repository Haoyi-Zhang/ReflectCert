final class UnsupportedInput {
    void resolve(String name) throws Exception {
        java.lang.Class.forName(name);
    }
}
