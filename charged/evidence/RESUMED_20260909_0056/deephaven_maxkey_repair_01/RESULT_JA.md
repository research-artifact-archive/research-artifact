# Maximum-key traversal repair

All6 new regression cells succeeded: maximum and near-maximum terminal keys crossed with viewport lengths0,1,2. Each returned expandedSize2, the expected requested rows and values, and exactly3V_NODE entries. The first source build/test took28.68seconds. Original unpatched diagnostics, including the observed9-entry prefix and the earlier output-chunk cleanup failure, remain unchanged in deephaven_resource_01.

The repair adds three lines after the non-fill iterator advance. If the selected terminal key isMAX, all smaller remaining keys have been consumed, and the existing consumeRemainder helper consumes the possible oneMAX key. This prevents repeating the same expanded row. The caller still visits that row once, so the patch preserves last-row expansion. These finite tests support the local argument. No claim is made about arbitrary structural updates, hash rehashes, user functions or whole CPU cost.

The current local upstream checkout now contains this author patch in addition to the optional policy hooks. Saved deephaven_policy_01 sources and its84-cell result still refer to the pre-repair source. No upstream issue, PR, external message or publication was sent.
