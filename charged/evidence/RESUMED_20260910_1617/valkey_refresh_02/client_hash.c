#include <stdint.h>
#include "sha1.h"
unsigned long long RetryHash(const unsigned char *p, uint32_t n, unsigned char *digest) {
 unsigned long long before=RetrySHA1Count(); SHA1_CTX c; SHA1Init(&c); SHA1Update(&c,p,n); SHA1Final(digest,&c); return RetrySHA1Count()-before;
}
