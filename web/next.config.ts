import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  // Phase 2: dev-indicator («Rendering…» в углу) часто срабатывает на больших
  // /search route с многими client-компонентами и визуально пугает. В prod его
  // нет; в dev сдвигаем в bottom-left чтобы не перекрывал ResultCard и
  // showcase-bar, плюс убираем ISR-badge (он бесполезен для нашего setup).
  devIndicators: {
    position: "bottom-left",
  },
};

export default withNextIntl(nextConfig);
