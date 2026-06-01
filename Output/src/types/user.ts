/**
 * types/user.ts
 * Derived from backend serializers exactly — Rule 10.
 * Source: apps/users/serializers.py → UserSerializer, UserProfileSerializer
 *
 * NOTE: profile can be null for accounts created before the Phase 4 signal
 * was wired. All profile access must use optional chaining: user.profile?.display_name
 */

export type AgeGroup = "Kids" | "Teens" | "Adults";

// Matches UserProfileSerializer output
// Source: apps/users/serializers.py → UserProfileSerializer
export interface UserProfile {
  display_name: string | null;
  avatar_url: string | null;
  age_group: AgeGroup | null;
  bio: string | null;
  interests: string[];
}

// Matches UserSerializer output
// Source: apps/users/serializers.py → UserSerializer
// profile is null for accounts created before the post_save signal was active
export interface User {
  id: string;
  email: string;
  is_email_verified: boolean;
  is_staff: boolean;
  created_at: string;
  profile: UserProfile | null;
}

// Payload for PATCH /api/v1/auth/me/
// Source: apps/users/serializers.py → UpdateProfileSerializer
export interface UpdateProfilePayload {
  display_name?: string;
  avatar_url?: string;
  age_group?: AgeGroup;
  bio?: string;
  interests?: string[];
}