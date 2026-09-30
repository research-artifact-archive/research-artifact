# Independent checker correction before measurement

The first static endpoint checker incorrectly allowed an ordinary action when no selected-version local component owned that action. This made old endpoint ready_i appear as a disabled uncontrollable move. E1 requires an owner; the checker is corrected to skip actions outside the union of the selected-version plant alphabets. The input models are unchanged. Both failed static validation outputs are retained under v1/validation/. No synthesis was run before this correction.
