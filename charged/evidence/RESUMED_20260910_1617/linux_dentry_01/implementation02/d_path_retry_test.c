// SPDX-License-Identifier: GPL-2.0
/* Author source integration tests; included in fs/d_path.c for its static body. */
#include <kunit/test.h>
#include <linux/completion.h>
#include <linux/kthread.h>
#include <linux/mount.h>
#include <linux/namei.h>
#include <linux/pseudo_fs.h>
#include <linux/sched.h>
#include <linux/smp.h>
#include <linux/wait.h>
#include "d_path_retry_inputs.h"

struct dp_body {
	u64 visits, copy, fill, chars;
	bool protected;
};

struct dp_context {
	struct task_struct *reader, *writer;
	struct vfsmount *mount;
	struct dentry *owned[84], *query, *moving, *target;
	unsigned int owned_count, kind, request, done, writes;
	wait_queue_head_t work_wq, done_wq;
	const struct dp_case *input;
	const struct dp_profile *profile;
	bool enabled, measuring, mid_issued;
	unsigned int end_issued, body_count, Q, guards, rcu_sections;
	unsigned int snapshot_steps, snapshot_takes, snapshot_releases;
	unsigned int snapshot_ref_inc, snapshot_ref_dec, snapshot_fallback;
	u64 snapshot_inline_bytes, snapshot_alloc_bytes, nonbody_chars;
	struct dp_body bodies[4];
	int error;
};

/* Static lifetime also makes disabled hooks safe for unrelated kernel tasks. */
static struct dp_context dp_ctx;

static struct dp_context *dp_current(void)
{
	if (!READ_ONCE(dp_ctx.enabled) || current != READ_ONCE(dp_ctx.reader))
		return NULL;
	return &dp_ctx;
}

static void dpath_body_begin(bool protected)
{
	struct dp_context *c = dp_current();
	if (!c)
		return;
	if (c->body_count >= ARRAY_SIZE(c->bodies)) {
		c->error = -EOVERFLOW;
		return;
	}
	c->bodies[c->body_count++].protected = protected;
	c->measuring = true;
}

static void dpath_body_end(void)
{
	struct dp_context *c = dp_current();
	if (c)
		c->measuring = false;
}

static void dpath_name_event(void)
{
	struct dp_context *c = dp_current();
	if (c && c->measuring)
		c->bodies[c->body_count - 1].visits++;
}

static void dpath_copy_event(int len, bool fault)
{
	struct dp_context *c = dp_current();
	if (!c || !c->measuring)
		return;
	if (len < 0) {
		c->error = -ERANGE;
		return;
	}
	c->bodies[c->body_count - 1].copy += len;
	if (fault)
		c->bodies[c->body_count - 1].fill += len;
}

static void dpath_char_event(void)
{
	struct dp_context *c = dp_current();
	if (!c)
		return;
	if (c->measuring)
		c->bodies[c->body_count - 1].chars++;
	else
		c->nonbody_chars++;
}

static void dpath_validation_event(void)
{
	struct dp_context *c = dp_current();
	if (c)
		c->Q++;
}

static void dpath_guard_event(void)
{
	struct dp_context *c = dp_current();
	if (c)
		c->guards++;
}

static void dpath_rcu_event(void)
{
	struct dp_context *c = dp_current();
	if (c)
		c->rcu_sections++;
}

static int dp_writer(void *arg)
{
	struct dp_context *c = arg;
	for (;;) {
		struct dentry *p1, *p2, *trap;
		unsigned int request;
		wait_event(c->work_wq,
			   READ_ONCE(c->request) != READ_ONCE(c->done) ||
			   kthread_should_stop());
		request = smp_load_acquire(&c->request);
		if (kthread_should_stop() && request == READ_ONCE(c->done))
			break;
		p1 = c->moving->d_parent;
		p2 = c->target->d_parent;
		trap = lock_rename(p1, p2);
		if (trap == c->moving || trap == c->target) {
			WRITE_ONCE(c->error, -EINVAL);
		} else {
			d_exchange(c->moving, c->target);
			WRITE_ONCE(c->writes, READ_ONCE(c->writes) + 1);
		}
		unlock_rename(p1, p2);
		smp_store_release(&c->done, request);
		wake_up(&c->done_wq);
	}
	return 0;
}

static void dp_trigger(struct dp_context *c, bool may_sleep)
{
	unsigned int request;
	if (READ_ONCE(c->error))
		return;
	request = READ_ONCE(c->request) + 1;
	smp_store_release(&c->request, request);
	wake_up(&c->work_wq);
	if (may_sleep) {
		if (!wait_event_timeout(c->done_wq,
				       smp_load_acquire(&c->done) == request,
				       msecs_to_jiffies(3000)))
			WRITE_ONCE(c->error, -ETIMEDOUT);
	} else {
		unsigned long deadline = jiffies + msecs_to_jiffies(3000);
		/* Reader pinned on CPU0, writer on CPU1. Never sleep in RCU. */
		while (smp_load_acquire(&c->done) != request) {
			if (time_after(jiffies, deadline)) {
				WRITE_ONCE(c->error, -ETIMEDOUT);
				break;
			}
			cpu_relax();
		}
	}
}

static void dpath_mid_gate(const struct dentry *dentry)
{
	struct dp_context *c = dp_current();
	if (!c || !c->profile->mid || c->mid_issued ||
	    c->body_count != 1 || !c->measuring ||
	    c->bodies[0].protected || dentry != c->query)
		return;
	c->mid_issued = true;
	dp_trigger(c, false);
}

static void dpath_end_gate(unsigned int phase)
{
	struct dp_context *c = dp_current();
	if (!c || phase > 1 || !(c->profile->gates & BIT(phase)) ||
	    (c->end_issued & BIT(phase)))
		return;
	c->end_issued |= BIT(phase);
	dp_trigger(c, true);
}

#include "cached_body.c.inc"

static int dp_fs_context(struct fs_context *fc)
{
	return init_pseudo(fc, 0x44505448) ? 0 : -ENOMEM;
}

static struct file_system_type dp_fs_type = {
	.name = "dpath-kunit",
	.init_fs_context = dp_fs_context,
	.kill_sb = kill_anon_super,
};

static struct dentry *dp_child(struct dp_context *c, struct dentry *parent,
			       const char *name, umode_t mode)
{
	struct dentry *d;
	struct inode *inode;
	if (c->owned_count >= ARRAY_SIZE(c->owned))
		return ERR_PTR(-EOVERFLOW);
	d = d_alloc_name(parent, name);
	if (!d)
		return ERR_PTR(-ENOMEM);
	inode = new_inode(parent->d_sb);
	if (!inode) {
		dput(d);
		return ERR_PTR(-ENOMEM);
	}
	inode->i_ino = iunique(parent->d_sb, 1);
	inode->i_mode = mode | 0755;
	set_nlink(inode, S_ISDIR(mode) ? 2 : 1);
	simple_inode_init_ts(inode);
	d_add(d, inode);
	c->owned[c->owned_count++] = d;
	return d;
}

static int dp_setup(struct dp_context *c, const struct dp_case *input)
{
	const struct dp_family *family = &dp_families[input->family];
	struct dentry *parent, *d, *alternate, *left, *right;
	unsigned int i;
	memset(c, 0, sizeof(*c));
	c->reader = current;
	c->input = input;
	c->profile = &dp_profiles[input->profile];
	init_waitqueue_head(&c->work_wq);
	init_waitqueue_head(&c->done_wq);
	c->mount = kern_mount(&dp_fs_type);
	if (IS_ERR(c->mount))
		return PTR_ERR(c->mount);
	parent = c->mount->mnt_root;
	for (i = 0; i < family->depth; i++) {
		d = dp_child(c, parent, family->names[i],
			     i + 1 == family->depth ? S_IFREG : S_IFDIR);
		if (IS_ERR(d))
			return PTR_ERR(d);
		parent = d;
	}
	c->query = parent;
	c->kind = !family->depth ? 1 : c->profile->kind;
	if (c->kind == 2 && family->depth < 2)
		c->kind = 0;
	alternate = dp_child(c, c->mount->mnt_root, family->alternate,
			     c->kind == 2 ? S_IFDIR : S_IFREG);
	if (IS_ERR(alternate))
		return PTR_ERR(alternate);
	left = dp_child(c, c->mount->mnt_root, "unrelated_left", S_IFREG);
	if (IS_ERR(left))
		return PTR_ERR(left);
	right = dp_child(c, c->mount->mnt_root, "unrelated_right", S_IFREG);
	if (IS_ERR(right))
		return PTR_ERR(right);
	c->moving = c->kind == 1 ? left :
		(c->kind == 2 ? c->owned[family->depth - 2] : c->query);
	c->target = c->kind == 1 ? right : alternate;
	c->writer = kthread_create(dp_writer, c, "dpath-writer");
	if (IS_ERR(c->writer))
		return PTR_ERR(c->writer);
	kthread_bind(c->writer, 1);
	wake_up_process(c->writer);
	return 0;
}

static void dp_cleanup(struct dp_context *c)
{
	WRITE_ONCE(c->enabled, false);
	if (!IS_ERR_OR_NULL(c->writer))
		kthread_stop(c->writer);
	while (c->owned_count)
		dput(c->owned[--c->owned_count]);
	if (!IS_ERR_OR_NULL(c->mount))
		kern_unmount(c->mount);
}

/* A stronger API: collect immutable names under protection, copy outside. */
static char *dpath_snapshot_raw(const struct dentry *dentry, char *buf, int cap)
{
	DECLARE_BUFFER(p, buf, cap);
	struct prepend_buffer b;
	struct name_snapshot *names;
	struct dp_context *c = dp_current();
	const struct dentry *cur = dentry;
	unsigned int slots = min_t(unsigned int, cap - 1, 64), used = 0, i;
	int remaining = cap - 1;
	bool overflow = false, fallback = false;

	names = slots ? kcalloc(slots, sizeof(*names), GFP_KERNEL) : NULL;
	if (slots && !names) {
		if (c)
			c->snapshot_fallback++;
		return dentry_path_raw(dentry, buf, cap);
	}
	if (c)
		c->snapshot_alloc_bytes += slots * sizeof(*names);
	prepend_char(&p, 0);
	b = p;
	dpath_end_gate(0);
	dpath_validation_event();
	dpath_guard_event();
	read_seqlock_excl(&rename_lock);
	while (!IS_ROOT(cur)) {
		unsigned int len = cur->d_name.len;
		if (c)
			c->snapshot_steps++;
		if ((u64)len + 1 > remaining) {
			overflow = true;
			break;
		}
		if (used == slots) {
			fallback = true;
			if (c)
				c->snapshot_fallback++;
			b = p;
			__dentry_path_body(dentry, &b, true);
			break;
		}
		if (c) {
			c->snapshot_takes++;
			if (cur->d_name.name == cur->d_iname)
				c->snapshot_inline_bytes += len + 1;
			else
				c->snapshot_ref_inc++;
		}
		take_dentry_name_snapshot(&names[used++], (struct dentry *)cur);
		remaining -= len + 1;
		cur = cur->d_parent;
	}
	read_sequnlock_excl(&rename_lock);
	if (!fallback && !overflow) {
		dpath_body_begin(false);
		for (i = 0; i < used; i++) {
			dpath_name_event();
			if (!prepend_name(&b, &names[i].name))
				break;
		}
		dpath_body_end();
	}
	for (i = 0; i < used; i++) {
		if (c) {
			c->snapshot_releases++;
			if (names[i].name.name != names[i].inline_name)
				c->snapshot_ref_dec++;
		}
		release_dentry_name_snapshot(&names[i]);
	}
	kfree(names);
	if (overflow)
		return ERR_PTR(-ENAMETOOLONG);
	if (b.len == p.len)
		prepend_char(&b, '/');
	return extract_string(&b);
}

static u64 dp_hash(const char *s)
{
	u64 h = 14695981039346656037ULL;
	while (*s) {
		h ^= (unsigned char)*s++;
		h *= 1099511628211ULL;
	}
	return h;
}

/* Declarative fixture oracle: does not read dentry pointers or source bodies. */
static void dp_expected(const struct dp_context *c, char *buf, size_t size,
			unsigned int writes)
{
	const struct dp_family *f = &dp_families[c->input->family];
	unsigned int start = 0, i;
	size_t off = 0;
	bool changed = (writes & 1) && c->kind != 1 && f->depth;
	buf[0] = 0;
	if (changed) {
		off += scnprintf(buf + off, size - off, "/%s", f->alternate);
		start = c->kind == 2 ? f->depth - 1 : f->depth;
	}
	for (i = start; i < f->depth; i++)
		off += scnprintf(buf + off, size - off, "/%s", f->names[i]);
	if (!off)
		strscpy(buf, "/", size);
}

static bool dp_guards_ok(const unsigned char *storage, unsigned int cap)
{
	unsigned int i;
	for (i = 0; i < 16; i++)
		if (storage[i] != 0xa5 || storage[16 + cap + i] != 0xa5)
			return false;
	return true;
}

static bool dp_one(struct kunit *test, const struct dp_case *input)
{
	struct dp_context *c = &dp_ctx;
	char *expected = NULL, *reference = NULL, *result = NULL, *ref;
	unsigned char *storage = NULL;
	unsigned int i, writes, before_writes, total_writes, expected_len = 0;
	u64 work = 0, protected_work = 0, bytes = 0, protected_bytes = 0;
	u64 visits = 0, protected_visits = 0, output_hash = 0, expected_hash = 0;
	u64 ceiling = 2ULL * (input->cap - 1) + 2;
	long error = 0, expected_error = 0, ref_error = 0, offset = -1;
	bool output_ok = false, reference_ok = false, canary = false;
	bool bounds = true, per_body = true, persistent = true, detected, healthy;
	int setup;

	setup = dp_setup(c, input);
	if (setup) {
		KUNIT_FAIL(test, "fixture %u failed: %d", input->id, setup);
		pr_info("DPROW {\"id\":%u,\"status\":\"SETUP_ERROR\",\"error\":%d}\n",
			input->id, setup);
		dp_cleanup(c);
		return false;
	}
	storage = kmalloc(input->cap + 32, GFP_KERNEL);
	expected = kmalloc(32768, GFP_KERNEL);
	reference = kmalloc(input->cap, GFP_KERNEL);
	if (!storage || !expected || !reference) {
		KUNIT_FAIL(test, "scratch allocation %u failed", input->id);
		pr_info("DPROW {\"id\":%u,\"status\":\"ALLOCATION_ERROR\"}\n", input->id);
		goto failure;
	}
	memset(storage, 0xa5, input->cap + 32);
	WRITE_ONCE(c->enabled, true);
	if (c->profile->pre)
		dp_trigger(c, true);
	before_writes = READ_ONCE(c->writes);
	switch (input->policy) {
	case 0:
		result = dentry_path_raw(c->query, (char *)storage + 16, input->cap);
		break;
	case 1:
		result = dpath_cached_raw(c->query, (char *)storage + 16, input->cap,
					 input->mutation);
		break;
	case 2:
		result = dpath_locked_raw(c->query, (char *)storage + 16, input->cap);
		break;
	case 3:
		result = dpath_snapshot_raw(c->query, (char *)storage + 16, input->cap);
		break;
	case 4:
		result = dpath_two_cheap_raw(c->query, (char *)storage + 16, input->cap);
		break;
	}
	WRITE_ONCE(c->enabled, false);
	writes = READ_ONCE(c->writes) - before_writes;
	dp_expected(c, expected, 32768, writes + before_writes);
	expected_len = strlen(expected);
	expected_error = expected_len + 1 > input->cap ? -ENAMETOOLONG : 0;
	expected_hash = expected_error ? 0 : dp_hash(expected);
	if (IS_ERR(result)) {
		error = PTR_ERR(result);
		output_ok = error == expected_error;
	} else if (result >= (char *)storage + 16 &&
		   result < (char *)storage + 16 + input->cap &&
		   memchr(result, 0, (char *)storage + 16 + input->cap - result)) {
		offset = result - ((char *)storage + 16);
		output_hash = dp_hash(result);
		output_ok = !expected_error && !strcmp(result, expected) &&
			    offset == input->cap - 1 - expected_len;
	}
	ref = dentry_path_raw(c->query, reference, input->cap);
	ref_error = IS_ERR(ref) ? PTR_ERR(ref) : 0;
	reference_ok = ref_error == expected_error &&
		(IS_ERR(ref) || !strcmp(ref, expected));
	canary = dp_guards_ok(storage, input->cap);
	for (i = 0; i < c->body_count; i++) {
		const struct dp_body *b = &c->bodies[i];
		u64 demand = b->copy + b->fill + b->chars;
		u64 cost = 1 + b->visits + demand;
		work += cost;
		bytes += demand;
		visits += b->visits;
		if (b->protected) {
			protected_work += cost;
			protected_bytes += demand;
			protected_visits += b->visits;
		}
		per_body &= b->visits <= input->cap &&
			b->visits <= b->chars + 1 && b->fill <= b->copy &&
			b->copy + b->chars <= input->cap - 1 &&
			b->fill <= input->cap - 1 && cost <= ceiling;
		pr_info("DPBODY {\"id\":%u,\"body\":%u,\"protected\":%u,"
			"\"visits\":%llu,\"copy\":%llu,\"fill\":%llu,"
			"\"chars\":%llu,\"T\":%llu}\n", input->id, i,
			b->protected, b->visits, b->copy, b->fill, b->chars, cost);
	}
	if (input->policy == 1 || input->policy == 4) {
		unsigned int allowed = 1 + min(writes, 2U);
		bounds = c->Q <= (input->policy == 4 ? 3 : 2) &&
			 c->body_count <= allowed &&
			 work <= allowed * ceiling &&
			 protected_work <= (writes >= 2 ? ceiling : 0);
	} else if (input->policy == 0) {
		bounds = c->Q <= 2 && c->body_count <= 1 + min(writes, 1U) &&
			 protected_work <= (writes ? ceiling : 0);
	} else if (input->policy == 2) {
		bounds = c->Q == 1 && c->body_count == 1;
	} else {
		bounds = c->Q <= 2 && c->snapshot_takes == c->snapshot_releases &&
			 c->snapshot_ref_inc == c->snapshot_ref_dec;
	}
	if (c->profile->late) {
		dp_trigger(c, true);
		if (!IS_ERR(result) && output_ok)
			persistent = dp_hash(result) == output_hash;
	}
	total_writes = READ_ONCE(c->writes);
	healthy = !READ_ONCE(c->error) && reference_ok && canary && persistent;
	detected = !output_ok || !bounds || !per_body;
	pr_info("DPROW {\"id\":%u,\"status\":\"%s\",\"B\":%u,"
		"\"writes_total\":%u,\"issued_end\":%u,\"issued_mid\":%u,"
		"\"Q\":%u,\"bodies\":%u,\"T\":%llu,\"L_T\":%llu,"
		"\"byte_demand\":%llu,\"protected_byte_demand\":%llu,"
		"\"visits\":%llu,\"protected_visits\":%llu,"
		"\"error\":%ld,\"expected_error\":%ld,"
		"\"expected_length\":%u,\"offset\":%ld,"
		"\"output_hash\":%llu,\"expected_hash\":%llu,"
		"\"output_ok\":%u,\"reference_ok\":%u,\"canary_ok\":%u,"
		"\"bounds_ok\":%u,\"per_body_ok\":%u,\"persistent\":%u,"
		"\"control_detected\":%u,\"internal_error\":%d}\n",
		input->id, healthy && (input->control ? detected : !detected) ?
		(input->control ? "CONTROL_DETECTED" : "SUCCESS") : "FAILURE",
		writes, total_writes, c->end_issued, c->mid_issued,
		c->Q, c->body_count, work, protected_work, bytes, protected_bytes,
		visits, protected_visits, error, expected_error,
		expected_len, offset, output_hash, expected_hash, output_ok,
		reference_ok, canary, bounds, per_body, persistent, detected,
		READ_ONCE(c->error));
	pr_info("DPAUX {\"id\":%u,\"guards\":%u,\"rcu\":%u,\"pre_writes\":%u,"
		"\"nonbody_chars\":%llu,\"snapshot_steps\":%u,"
		"\"snapshot_takes\":%u,\"snapshot_releases\":%u,"
		"\"ref_inc\":%u,\"ref_dec\":%u,"
		"\"snapshot_inline_bytes\":%llu,\"snapshot_alloc_bytes\":%llu,"
		"\"snapshot_fallback\":%u}\n", input->id, c->guards,
		c->rcu_sections, before_writes, c->nonbody_chars, c->snapshot_steps,
		c->snapshot_takes, c->snapshot_releases, c->snapshot_ref_inc,
		c->snapshot_ref_dec, c->snapshot_inline_bytes,
		c->snapshot_alloc_bytes, c->snapshot_fallback);
	KUNIT_EXPECT_TRUE_MSG(test, healthy, "row %u environment/oracle", input->id);
	KUNIT_EXPECT_EQ_MSG(test, detected, input->control,
			   "row %u policy/control", input->id);
	kfree(storage);
	kfree(expected);
	kfree(reference);
	dp_cleanup(c);
	return healthy;
failure:
	kfree(storage);
	kfree(expected);
	kfree(reference);
	dp_cleanup(c);
	return false;
}

static void dpath_resource_group(struct kunit *test, unsigned int group)
{
	cpumask_t previous;
	unsigned int i;
	bool active = true;
	int err;
	KUNIT_ASSERT_TRUE(test, cpu_online(0) && cpu_online(1));
	cpumask_copy(&previous, current->cpus_ptr);
	err = set_cpus_allowed_ptr(current, cpumask_of(0));
	KUNIT_ASSERT_EQ(test, err, 0);
	err = register_filesystem(&dp_fs_type);
	if (err) {
		KUNIT_FAIL(test, "register_filesystem: %d", err);
		set_cpus_allowed_ptr(current, &previous);
		return;
	}
	if (!group)
	pr_info("DPMETA {\"planned\":%zu,\"valid\":1920,\"controls\":4,"
		"\"inline_name_bytes\":%zu,\"snapshot_size\":%zu,\"cpus\":%u}\n",
		ARRAY_SIZE(dp_cases), sizeof(((struct dentry *)0)->d_iname),
		sizeof(struct name_snapshot), num_online_cpus());
	for (i = 0; i < ARRAY_SIZE(dp_cases); i++) {
		const struct dp_case *spec = &dp_cases[i];
		if ((spec->control ? 8 : spec->family) != group)
			continue;
		if (kthread_should_stop())
			active = false;
		if (active)
			active = dp_one(test, &dp_cases[i]);
		else
			pr_info("DPROW {\"id\":%u,\"status\":\"NOT_EXECUTED\"}\n", i);
	}
	unregister_filesystem(&dp_fs_type);
	set_cpus_allowed_ptr(current, &previous);
}

#define DP_GROUP_TEST(index) \
	static void dpath_group_##index(struct kunit *test) \
	{ dpath_resource_group(test, index); }
DP_GROUP_TEST(0)
DP_GROUP_TEST(1)
DP_GROUP_TEST(2)
DP_GROUP_TEST(3)
DP_GROUP_TEST(4)
DP_GROUP_TEST(5)
DP_GROUP_TEST(6)
DP_GROUP_TEST(7)
DP_GROUP_TEST(8)

static struct kunit_case dpath_retry_cases[] = {
	KUNIT_CASE_SLOW(dpath_group_0),
	KUNIT_CASE_SLOW(dpath_group_1),
	KUNIT_CASE_SLOW(dpath_group_2),
	KUNIT_CASE_SLOW(dpath_group_3),
	KUNIT_CASE_SLOW(dpath_group_4),
	KUNIT_CASE_SLOW(dpath_group_5),
	KUNIT_CASE_SLOW(dpath_group_6),
	KUNIT_CASE_SLOW(dpath_group_7),
	KUNIT_CASE(dpath_group_8),
	{}
};

static struct kunit_suite dpath_retry_suite = {
	.name = "dpath-retry",
	.test_cases = dpath_retry_cases,
};

kunit_test_suite(dpath_retry_suite);
