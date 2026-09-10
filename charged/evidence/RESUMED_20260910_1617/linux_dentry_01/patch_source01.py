from pathlib import Path
import hashlib, difflib, json, datetime
D = Path(__file__).resolve().parent
source = D/'upstream-source/fs/d_path.c'
original = source.read_text()
s = original
def replace(old, new):
    global s
    assert s.count(old) == 1, (old[:90], s.count(old))
    s = s.replace(old, new)
hooks = '''
#ifdef CONFIG_D_PATH_KUNIT_TEST
#include "d_path_retry_hooks.h"
#else
#define dpath_body_begin(protected) do { } while (0)
#define dpath_body_end() do { } while (0)
#define dpath_name_event() do { } while (0)
#define dpath_copy_event(len, fault) do { } while (0)
#define dpath_char_event() do { } while (0)
#define dpath_mid_gate(dentry) do { } while (0)
#define dpath_end_gate(phase) do { } while (0)
#define dpath_validation_event() do { } while (0)
#define dpath_guard_event() do { } while (0)
#define dpath_rcu_event() do { } while (0)
#endif
'''
replace('#include "internal.h"\n', '#include "internal.h"\n' + hooks)
replace('\t\t*--p->buf = c;\n', '\t\t*--p->buf = c;\n\t\tdpath_char_event();\n')
replace("\t\tmemset(dst, 'x', len);\n\t\treturn false;\n\t}\n\treturn true;\n}",
        "\t\tdpath_copy_event(len, true);\n\t\tmemset(dst, 'x', len);\n\t\treturn false;\n\t}\n\tdpath_copy_event(len, false);\n\treturn true;\n}")
old_loop = '''\twhile (!IS_ROOT(dentry)) {
\t\tconst struct dentry *parent = dentry->d_parent;

\t\tprefetch(parent);
\t\tif (!prepend_name(&b, &dentry->d_name))
\t\t\tbreak;
\t\tdentry = parent;
\t}'''
assert s.count(old_loop) == 1
body_loop = old_loop.replace('\t\tprefetch(parent);', '\t\tdpath_name_event();\n\t\tdpath_mid_gate(dentry);\n\t\tprefetch(parent);').replace('prepend_name(&b,', 'prepend_name(b,')
new_body = '''/* The upstream traversal is factored without changing its operations. */
static void __dentry_path_body(const struct dentry *dentry,
\t\t\t       struct prepend_buffer *b, bool protected)
{
\tdpath_body_begin(protected);
''' + body_loop + '''
\tdpath_body_end();
}

'''
needle = 'static char *__dentry_path(const struct dentry *d, struct prepend_buffer *p)'
replace(needle, new_body + needle)
replace(old_loop, '\t__dentry_path_body(dentry, &b, seq & 1);')
replace('''\trcu_read_lock();
restart:
\tdentry = d;
\tb = *p;
\tread_seqbegin_or_lock(&rename_lock, &seq);''', '''\tdpath_rcu_event();
\trcu_read_lock();
restart:
\tdentry = d;
\tb = *p;
\tif (seq & 1) {
\t\tdpath_end_gate(1);
\t\tdpath_validation_event();
\t\tdpath_guard_event();
\t}
\tread_seqbegin_or_lock(&rename_lock, &seq);''')
replace('''\t__dentry_path_body(dentry, &b, seq & 1);
\tif (!(seq & 1))
\t\trcu_read_unlock();
\tif (need_seqretry(&rename_lock, seq)) {''', '''\t__dentry_path_body(dentry, &b, seq & 1);
\tif (!(seq & 1)) {
\t\trcu_read_unlock();
\t\tdpath_end_gate(0);
\t\tdpath_validation_event();
\t}
\tif (need_seqretry(&rename_lock, seq)) {''')
s += '\n#ifdef CONFIG_D_PATH_KUNIT_TEST\n#include "d_path_retry_test.c"\n#endif\n'
out = D/'implementation01/d_path.c'
with out.open('x') as f: f.write(s)
diff = ''.join(difflib.unified_diff(original.splitlines(True), s.splitlines(True), fromfile='a/fs/d_path.c', tofile='b/fs/d_path.c'))
with (D/'implementation01/d_path.patch').open('x') as f: f.write(diff)
row = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(), role='KUnit-only source integration; upstream traversal factored, baseline control flow retained; event hooks and scripted schedules compiled only for this test')
with (D/'SOURCE_PATCH_RECEIPT01.json').open('x') as f: json.dump(row, f, indent=2); f.write('\n')
print(json.dumps(row, indent=2))
