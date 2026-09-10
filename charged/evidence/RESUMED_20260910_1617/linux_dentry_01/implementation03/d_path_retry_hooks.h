/* SPDX-License-Identifier: GPL-2.0 */
/* Author instrumentation. Counts source events, not elapsed/native cycles. */
static void dpath_body_begin(bool protected);
static void dpath_body_end(void);
static void dpath_name_event(void);
static void dpath_copy_event(int len, bool fault);
static void dpath_char_event(void);
static void dpath_mid_gate(const struct dentry *dentry);
static void dpath_end_gate(unsigned int phase);
static void dpath_validation_event(void);
static void dpath_guard_event(void);
static void dpath_rcu_event(void);
