final class UnsupportedInput {
    void resolve(String name) throws Exception {
        Class.forName(name);
    }
}
