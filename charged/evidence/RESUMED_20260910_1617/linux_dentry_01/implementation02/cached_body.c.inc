/* SPDX-License-Identifier: GPL-2.0 */
/* Research variant, same source traversal; mutation flags are test-only. */
static char *dpath_cached_raw(const struct dentry *dentry, char *buf,
			     int buflen, unsigned int mutation)
{
	DECLARE_BUFFER(p, buf, buflen);
	struct prepend_buffer b;
	unsigned int s1, s2;

	prepend_char(&p, 0);
	dpath_rcu_event();
	rcu_read_lock();
	s1 = read_seqbegin(&rename_lock);
	b = p;
	__dentry_path_body(dentry, &b, false);
	rcu_read_unlock();
	if (mutation == 4 && b.len < 0)
		goto finish;
	dpath_end_gate(0);
	dpath_validation_event();
	if (!read_seqretry(&rename_lock, s1))
		goto finish;

	dpath_rcu_event();
	rcu_read_lock();
	s2 = mutation == 2 ? s1 : read_seqbegin(&rename_lock);
	if (mutation != 3)
		b = p;
	__dentry_path_body(dentry, &b, false);
	rcu_read_unlock();
	dpath_end_gate(1);
	dpath_validation_event();
	dpath_guard_event();
	read_seqlock_excl(&rename_lock);
	if (mutation != 1 && read_seqretry(&rename_lock, s2)) {
		b = p;
		__dentry_path_body(dentry, &b, true);
	}
	read_sequnlock_excl(&rename_lock);
finish:
	if (b.len == p.len)
		prepend_char(&b, '/');
	return extract_string(&b);
}

static char *dpath_locked_raw(const struct dentry *dentry, char *buf, int buflen)
{
	DECLARE_BUFFER(p, buf, buflen);
	struct prepend_buffer b;

	prepend_char(&p, 0);
	b = p;
	dpath_end_gate(0);
	dpath_validation_event();
	dpath_guard_event();
	read_seqlock_excl(&rename_lock);
	__dentry_path_body(dentry, &b, true);
	read_sequnlock_excl(&rename_lock);
	if (b.len == p.len)
		prepend_char(&b, '/');
	return extract_string(&b);
}

/* A higher-call-cap comparator: two lockless validations, then fresh. */
static char *dpath_two_cheap_raw(const struct dentry *dentry, char *buf, int buflen)
{
	DECLARE_BUFFER(p, buf, buflen);
	struct prepend_buffer b;
	unsigned int seq, attempt;

	prepend_char(&p, 0);
	for (attempt = 0; attempt < 2; attempt++) {
		dpath_rcu_event();
		rcu_read_lock();
		seq = read_seqbegin(&rename_lock);
		b = p;
		__dentry_path_body(dentry, &b, false);
		rcu_read_unlock();
		dpath_end_gate(attempt);
		dpath_validation_event();
		if (!read_seqretry(&rename_lock, seq))
			goto finish;
	}
	dpath_validation_event();
	dpath_guard_event();
	read_seqlock_excl(&rename_lock);
	b = p;
	__dentry_path_body(dentry, &b, true);
	read_sequnlock_excl(&rename_lock);
finish:
	if (b.len == p.len)
		prepend_char(&b, '/');
	return extract_string(&b);
}
