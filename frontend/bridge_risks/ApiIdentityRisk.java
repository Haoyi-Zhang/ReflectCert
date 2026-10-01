final class ApiIdentityRisk {
    static final class ShadowTarget {}
    static final class LoaderTarget {}

    static final class Class {
        static java.lang.Class<?> forName(String ignored) {
            return ShadowTarget.class;
        }
    }

    static final class RedirectingLoader extends ClassLoader {
        @Override
        public java.lang.Class<?> loadClass(String ignored) {
            return LoaderTarget.class;
        }
    }

    static final class Holder {
        ClassLoader getClassLoader() {
            return new RedirectingLoader();
        }
    }

    ClassLoader getClassLoader() {
        return new RedirectingLoader();
    }

    static String shadowedClass() throws Exception {
        return Class.forName("java.lang.String").getSimpleName();
    }

    String customThisGetter() throws Exception {
        return getClassLoader().loadClass("java.lang.String").getSimpleName();
    }

    static String customObjectGetter() throws Exception {
        Holder holder = new Holder();
        return holder.getClassLoader().loadClass("java.lang.String").getSimpleName();
    }

    public static void main(String[] args) throws Exception {
        ApiIdentityRisk self = new ApiIdentityRisk();
        System.out.println(shadowedClass() + "\t" + self.customThisGetter() + "\t" +
                customObjectGetter());
    }
}
