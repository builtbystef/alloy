/** "Step 1 of 2" above an onboarding card's title. */
export const ONBOARDING_STEPS = 2;

export function OnboardingSteps({ current }: { current: number }) {
  return (
    <p className="text-sm font-medium text-muted-foreground">
      Step {current} of {ONBOARDING_STEPS}
    </p>
  );
}
