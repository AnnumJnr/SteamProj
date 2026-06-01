/**
 * components/combo/ComboCard.tsx
 * Combo card for grids. Renders title, metadata, course count, and rating.
 * No data fetching. No navigation. Receives combo data as a prop.
 * Field name corrections from backend ComboListSerializer:
 *   average_rating  (not rating_average)
 *   rating_count
 *   created_by_type (not created_by)
 * Source: apps/combos/serializers.py → ComboListSerializer
 */
 
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatRating, formatRatingCount } from "@/lib/utils";
import type { Combo } from "@/types/combo";
 
interface ComboCardProps {
  combo: Combo;
}
 
const difficultyVariant = (difficulty: string): "success" | "warning" | "danger" | "muted" => {
  if (difficulty === "Beginner") return "success";
  if (difficulty === "Intermediate") return "warning";
  if (difficulty === "Advanced") return "danger";
  return "muted";
};
 
const CATEGORY_COLOURS: Record<string, string> = {
  "Computer Science":          "bg-blue-400",
  "Mathematics":               "bg-purple-400",
  "Natural Sciences":          "bg-green-400",
  "Engineering":               "bg-orange-400",
  "Technology & Applied Skills": "bg-cyan-400",
  "STEM Foundations":          "bg-pink-400",
};
 
export function ComboCard({ combo }: ComboCardProps) {
  const colourDot = CATEGORY_COLOURS[combo.category] ?? "bg-primary";
 
  return (
    <Card variant="interactive" className="flex flex-col h-full p-5 gap-4">
 
      {/* Category + featured */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${colourDot}`} />
          <span className="text-xs font-medium text-text-muted">{combo.category || "STEM"}</span>
        </div>
        {combo.is_featured && (
          <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-warning/20 text-warning border border-warning/30">
            Featured
          </span>
        )}
        {!combo.is_public && (
          <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-surface-overlay text-text-muted border border-surface-border">
            Private
          </span>
        )}
      </div>
 
      {/* Title and description */}
      <div className="flex-1">
        <h3 className="text-sm font-semibold text-text-primary line-clamp-2 mb-2 leading-snug">
          {combo.title}
        </h3>
        <p className="text-xs text-text-secondary line-clamp-3 leading-relaxed">
          {combo.short_description}
        </p>
      </div>
 
      {/* Badges */}
      <div className="flex gap-1.5 flex-wrap">
        <Badge variant={difficultyVariant(combo.difficulty)}>
          {combo.difficulty}
        </Badge>
        {combo.recommended_age && combo.recommended_age !== "All Ages" && (
          <Badge variant="muted">{combo.recommended_age}</Badge>
        )}
      </div>
 
      {/* Meta footer */}
      <div className="flex items-center justify-between pt-3 border-t border-surface-border">
 
        {/* Course count + duration */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 text-text-muted">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            <span className="text-xs">{combo.course_count} courses</span>
          </div>
          {combo.estimated_weeks > 0 && (
            <div className="flex items-center gap-1 text-text-muted">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span className="text-xs">{combo.estimated_weeks}w</span>
            </div>
          )}
        </div>
 
        {/* Rating — uses average_rating (correct field name) */}
        {(combo.average_rating ?? 0) > 0 ? (
          <div className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5 text-warning" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            <span className="text-xs font-semibold text-text-primary">
              {formatRating(combo.average_rating!)}
            </span>
            <span className="text-xs text-text-muted">
              ({formatRatingCount(combo.rating_count)})
            </span>
          </div>
        ) : (
          <span className="text-xs text-text-muted">No ratings yet</span>
        )}
      </div>
 
      {/* Start path CTA */}
      <div className="flex items-center gap-1.5 text-primary text-xs font-semibold">
        <span>View Path</span>
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 8l4 4m0 0l-4 4m4-4H3" />
        </svg>
      </div>
    </Card>
  );
}
 