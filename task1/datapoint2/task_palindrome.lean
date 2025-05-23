def isPalindrome (xs : List Nat) : Bool :=
  -- << CODE START >>
  xs == xs.reverse
  -- << CODE END >>

def isPalindrome_spec_def (xs : List Nat) (result : Bool) : Prop :=
  -- << SPEC START >>
  result = true ↔ xs = xs.reverse
  -- << SPEC END >>