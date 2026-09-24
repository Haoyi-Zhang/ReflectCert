final class UnsupportedParameter {
    void resolve(Class<?> parameterType) throws Exception {
        Class<?> owner = Class.forName("pkg.A");
        owner.getMethod("run", parameterType);
    }
}
