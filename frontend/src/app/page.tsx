import { Hero } from "@/components/landing/hero";
import { Features } from "@/components/landing/features";
import { Pricing } from "@/components/landing/pricing";
import { ContactForm } from "@/components/landing/contact-form";
import { Footer } from "@/components/landing/footer";
import { Navbar } from "@/components/layout/navbar";

export default function LandingPage() {
  return (
    <main className="min-h-screen">
      <Navbar />
      <Hero />
      <Features />
      <Pricing />
      <ContactForm />
      <Footer />
    </main>
  );
}
