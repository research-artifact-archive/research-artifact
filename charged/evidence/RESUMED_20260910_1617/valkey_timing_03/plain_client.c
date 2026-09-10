#include <stdint.h>
#include "sha1.h"
void PlainHash(const unsigned char *p, uint32_t n, unsigned char *digest) { SHA1_CTX c; SHA1Init(&c); SHA1Update(&c,p,n); SHA1Final(digest,&c); }
