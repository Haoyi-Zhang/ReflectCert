final class SupportedFinite {
    void resolve(boolean h, boolean k) throws Exception {
        String prefix = "pkg.";
        boolean chooseA = h && !k;
        String className = prefix.concat(chooseA ? "A" : "B");
        Class<?> owner = Class.forName(className);
        owner.getMethod(h ? "run" : "stop", String.class);
    }
}
