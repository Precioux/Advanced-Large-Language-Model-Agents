def removeDuplicates (xs : List Nat) : List Nat :=
  -- << CODE START >>
  match xs with
  | [] => []
  | x :: xs =>
    let rec dedup (prev : Nat) (rest : List Nat) : List Nat :=
      match rest with
      | [] => []
      | y :: ys =>
        if y == prev then
          dedup prev ys
        else
          y :: dedup y ys
    x :: dedup x xs
  -- << CODE END >>

def removeDuplicates_spec_noConsecutiveDuplicates (xs : List Nat) (result : List Nat) : Prop :=
  -- << SPEC START >>
  (∀ i : Nat, i + 1 < result.length → result.get! i ≠ result.get! (i + 1)) ∧
  (∀ x : Nat, x ∈ result → x ∈ xs) ∧
  (result = [] ∨ result.head! = xs.head!)
  -- << SPEC END >>