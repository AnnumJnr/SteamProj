/**
 * app/page.tsx
 * Homepage. Server component that renders the hero and shells for featured content.
 * Client sub-components handle data fetching for featured combos and courses.
 */

import Link from "next/link";
import { Suspense } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/Button";
import { ROUTES } from "@/constants/routes";
import { FeaturedCombos } from "@/components/combo/FeaturedCombos";
import { FeaturedCourses } from "@/components/course/FeaturedCourses";
import { CategoryStrip } from "@/components/shared/CategoryStrip";
import { LoadingState } from "@/components/shared/LoadingState";

// ─── STEM Category icons (inline SVG) ─────────────────────────────────────

const CATEGORIES = [
  {
    label: "Computer Science",
    description: "Programming, algorithms, AI, data",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    ),
    href: `${ROUTES.COURSES}?category=Computer+Science`,
  },
  {
    label: "Mathematics",
    description: "Algebra, calculus, statistics",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    ),
    href: `${ROUTES.COURSES}?category=Mathematics`,
  },
  {
    label: "Natural Sciences",
    description: "Physics, chemistry, biology",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
      </svg>
    ),
    href: `${ROUTES.COURSES}?category=Natural+Sciences`,
  },
  {
    label: "Engineering",
    description: "Design, build, problem-solve",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    href: `${ROUTES.COURSES}?category=Engineering`,
  },
  {
    label: "Technology",
    description: "Applied skills, tools, careers",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
    href: `${ROUTES.COURSES}?category=Technology+%26+Applied+Skills`,
  },
  {
    label: "STEM Foundations",
    description: "Core concepts for beginners",
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    ),
    href: `${ROUTES.COURSES}?category=STEM+Foundations`,
  },
];

// ─── Stats ─────────────────────────────────────────────────────────────────

const STATS = [
  { value: "6", label: "STEM categories" },
  { value: "5+", label: "trusted providers" },
  { value: "Free", label: "to use, always" },
  { value: "All ages", label: "kids to adults" },
];

export default function HomePage() {
  return (
    <div className="flex flex-col">

      {/* ─── Hero ────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden bg-surface-base">
        {/* Background decoration */}
        <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
          <div className="absolute top-0 right-0 w-[600px] h-[600px] rounded-full bg-primary/5 blur-3xl translate-x-1/3 -translate-y-1/4" />
          <div className="absolute bottom-0 left-0 w-[400px] h-[400px] rounded-full bg-accent/5 blur-3xl -translate-x-1/3 translate-y-1/4" />
        </div>

        <PageContainer>
          <div className="relative py-24 md:py-32 flex flex-col items-center text-center gap-6 max-w-3xl mx-auto">

            {/* Eyebrow */}
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary-subtle border border-primary/20 text-primary text-xs font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-subtle" />
              Structured learning paths for every stage
            </div>

            {/* Headline */}
            <h1 className="text-5xl md:text-6xl font-display font-bold text-text-primary leading-tight">
              Your Path.{" "}
              <span className="text-primary">Your Pace.</span>
              <br />
              Your Future.
            </h1>

            {/* Subheadline */}
            <p className="text-lg text-text-secondary max-w-xl leading-relaxed">
              Curated STEM courses and structured Combo learning paths from the world&apos;s
              best free providers — all in one place.
            </p>

            {/* CTA buttons */}
            <div className="flex items-center gap-3 flex-wrap justify-center">
              <Link href={ROUTES.COURSES}>
                <Button size="lg">Explore Courses</Button>
              </Link>
              <Link href={ROUTES.COMBOS}>
                <Button size="lg" variant="secondary">Browse Combos</Button>
              </Link>
            </div>

            {/* Stats strip */}
            <div className="flex items-center gap-8 flex-wrap justify-center pt-4 border-t border-surface-border w-full mt-2">
              {STATS.map((stat) => (
                <div key={stat.label} className="text-center">
                  <div className="text-xl font-bold text-text-primary">{stat.value}</div>
                  <div className="text-xs text-text-muted">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </PageContainer>
      </section>

      {/* ─── Category Strip ──────────────────────────────────────────────── */}
      <section className="border-y border-surface-border bg-surface-raised py-10">
        <PageContainer>
          <h2 className="text-lg font-semibold text-text-primary mb-6">Browse by subject</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {CATEGORIES.map((cat) => (
              <Link
                key={cat.label}
                href={cat.href}
                className="flex flex-col items-center gap-2.5 p-4 rounded-xl bg-surface-overlay border border-surface-border
                           hover:border-primary hover:bg-primary-subtle transition-all duration-200 group text-center"
              >
                <span className="text-text-secondary group-hover:text-primary transition-colors duration-150">
                  {cat.icon}
                </span>
                <div>
                  <p className="text-sm font-medium text-text-primary group-hover:text-primary transition-colors duration-150 leading-tight">
                    {cat.label}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </PageContainer>
      </section>

      {/* ─── Featured Combo Paths ─────────────────────────────────────────── */}
      <section className="py-16 bg-surface-base">
        <PageContainer>
          <div className="flex items-end justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-text-primary mb-1">Popular Combo Paths</h2>
              <p className="text-sm text-text-secondary">
                Structured learning sequences built from the best free courses
              </p>
            </div>
            <Link href={ROUTES.COMBOS} className="text-sm text-primary hover:text-primary-hover font-medium transition-colors hidden sm:block">
              View all combos →
            </Link>
          </div>
          <Suspense fallback={<LoadingState message="Loading combo paths…" />}>
            <FeaturedCombos />
          </Suspense>
        </PageContainer>
      </section>

      {/* ─── Featured Courses ─────────────────────────────────────────────── */}
      <section className="py-16 bg-surface-raised border-t border-surface-border">
        <PageContainer>
          <div className="flex items-end justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-text-primary mb-1">Popular Courses</h2>
              <p className="text-sm text-text-secondary">
                Hand-picked from YouTube, MIT OCW, freeCodeCamp and more
              </p>
            </div>
            <Link href={ROUTES.COURSES} className="text-sm text-primary hover:text-primary-hover font-medium transition-colors hidden sm:block">
              View all courses →
            </Link>
          </div>
          <Suspense fallback={<LoadingState message="Loading courses…" />}>
            <FeaturedCourses />
          </Suspense>
        </PageContainer>
      </section>

      {/* ─── CTA Banner ──────────────────────────────────────────────────── */}
      <section className="py-16 bg-surface-base border-t border-surface-border">
        <PageContainer>
          <div className="relative rounded-2xl bg-gradient-to-br from-primary-subtle via-surface-raised to-surface-raised border border-primary/20 overflow-hidden px-8 py-12 text-center">
            <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
              <div className="absolute top-0 right-0 w-64 h-64 rounded-full bg-primary/10 blur-2xl" />
            </div>
            <div className="relative max-w-lg mx-auto">
              <h2 className="text-2xl font-bold text-text-primary mb-3">
                Ready to start learning?
              </h2>
              <p className="text-text-secondary mb-6 leading-relaxed">
                Create a free account and track your progress across every course and Combo path.
              </p>
              <div className="flex items-center gap-3 justify-center flex-wrap">
                <Link href={ROUTES.REGISTER}>
                  <Button size="lg">Get started free</Button>
                </Link>
                <Link href={ROUTES.COURSES}>
                  <Button size="lg" variant="ghost">Explore without signing up</Button>
                </Link>
              </div>
            </div>
          </div>
        </PageContainer>
      </section>

    </div>
  );
}
