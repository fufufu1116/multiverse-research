#if !defined(__x86_64__)
#error "v7r13 launcher requires linux amd64"
#endif

typedef unsigned long u64;
typedef long s64;

#ifndef V7R13_PROBE_PATH
#define V7R13_PROBE_PATH "/usr/local/bin/multiverse-v36-prearm-rate-readiness-v7r9"
#endif
#ifndef V7R13_AUTH_UID
#define V7R13_AUTH_UID 64173UL
#endif

static const char probe_path[] = V7R13_PROBE_PATH;
static const char env_codespaces[] = "CODESPACES=true";
static const char key_codespaces[] = "CODESPACES=";
static const char key_name[] = "CODESPACE_NAME=";
static const char arg_commit[] = "commit";
static char env_name[15 + 129];

#define SYS_close 3
#define SYS_chdir 80
#define SYS_getuid 102
#define SYS_geteuid 107
#define SYS_setresuid 117
#define SYS_getresuid 118
#define SYS_prctl 157
#define SYS_close_range 436
#define PR_SET_DUMPABLE 4
#define PR_SET_NO_NEW_PRIVS 38

static s64 xsys0(s64 nr) {
  register s64 rax __asm__("rax") = nr;
  __asm__ volatile("syscall" : "+r"(rax) : : "rcx", "r11", "memory");
  return rax;
}
static s64 xsys1(s64 nr, u64 a1) {
  register s64 rax __asm__("rax") = nr;
  register u64 rdi __asm__("rdi") = a1;
  __asm__ volatile("syscall" : "+r"(rax) : "r"(rdi) : "rcx", "r11", "memory");
  return rax;
}
static s64 xsys2(s64 nr, u64 a1, u64 a2) {
  register s64 rax __asm__("rax") = nr;
  register u64 rdi __asm__("rdi") = a1;
  register u64 rsi __asm__("rsi") = a2;
  __asm__ volatile("syscall" : "+r"(rax) : "r"(rdi), "r"(rsi) : "rcx", "r11", "memory");
  return rax;
}
static s64 xsys3(s64 nr, u64 a1, u64 a2, u64 a3) {
  register s64 rax __asm__("rax") = nr;
  register u64 rdi __asm__("rdi") = a1;
  register u64 rsi __asm__("rsi") = a2;
  register u64 rdx __asm__("rdx") = a3;
  __asm__ volatile("syscall" : "+r"(rax) : "r"(rdi), "r"(rsi), "r"(rdx) : "rcx", "r11", "memory");
  return rax;
}
static s64 xsys5(s64 nr, u64 a1, u64 a2, u64 a3, u64 a4, u64 a5) {
  register s64 rax __asm__("rax") = nr;
  register u64 rdi __asm__("rdi") = a1;
  register u64 rsi __asm__("rsi") = a2;
  register u64 rdx __asm__("rdx") = a3;
  register u64 r10 __asm__("r10") = a4;
  register u64 r8 __asm__("r8") = a5;
  __asm__ volatile("syscall" : "+r"(rax) : "r"(rdi), "r"(rsi), "r"(rdx), "r"(r10), "r"(r8) : "rcx", "r11", "memory");
  return rax;
}

static __attribute__((noreturn)) void xexit(int code) {
  register s64 rax __asm__("rax") = 60;
  register s64 rdi __asm__("rdi") = code;
  __asm__ volatile("syscall" : : "r"(rax), "r"(rdi) : "rcx", "r11", "memory");
  __builtin_unreachable();
}

static s64 xexecve(const char *p, char *const a[], char *const e[]) {
  register s64 rax __asm__("rax") = 59;
  register const char *rdi __asm__("rdi") = p;
  register char *const *rsi __asm__("rsi") = a;
  register char *const *rdx __asm__("rdx") = e;
  __asm__ volatile("syscall" : "+r"(rax) : "r"(rdi), "r"(rsi), "r"(rdx) : "rcx", "r11", "memory");
  return rax;
}

static int streq(const char *a, const char *b) {
  u64 i = 0;
  for (;;) {
    if (a[i] != b[i]) return 0;
    if (a[i] == 0) return 1;
    i++;
  }
}

static int starts(const char *s, const char *p) {
  u64 i = 0;
  while (p[i]) { if (s[i] != p[i]) return 0; i++; }
  return 1;
}

static int valid_name(const char *s, u64 *n_out) {
  u64 n = 0;
  for (; s[n]; n++) {
    unsigned char c = (unsigned char)s[n];
    if (n >= 128) return 0;
    if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-')) return 0;
  }
  if (n == 0) return 0;
  *n_out = n;
  return 1;
}

static int launcher_credentials(u64 *real_uid_out) {
  u64 r = 0, e = 0, s = 0;
  if (xsys0(SYS_geteuid) != 0) return 0;
  r = (u64)xsys0(SYS_getuid);
  if (r == 0 || r == V7R13_AUTH_UID) return 0;
  if (xsys3(SYS_getresuid, (u64)&r, (u64)&e, (u64)&s) < 0) return 0;
  if (e != 0 || s != 0) return 0;
  *real_uid_out = r;
  return 1;
}

static int establish_exec_boundary(u64 real_uid) {
  u64 r = 0, e = 0, s = 0;
  if (xsys5(SYS_prctl, PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0) return 0;
  if (xsys3(SYS_setresuid, real_uid, V7R13_AUTH_UID, V7R13_AUTH_UID) < 0) return 0;
  if (xsys3(SYS_getresuid, (u64)&r, (u64)&e, (u64)&s) < 0) return 0;
  if (r != real_uid || e != V7R13_AUTH_UID || s != V7R13_AUTH_UID) return 0;
  if (xsys5(SYS_prctl, PR_SET_DUMPABLE, 0, 0, 0, 0) < 0) return 0;
  return 1;
}

static __attribute__((noreturn)) void start_c(u64 *sp) {
  u64 real_uid = 0;
  if (!launcher_credentials(&real_uid)) xexit(92);

  u64 argc = sp[0];
  char **argv = (char **)&sp[1];
  char **envp = &argv[argc + 1];
  if (!(argc == 1 || (argc == 2 && streq(argv[1], arg_commit)))) xexit(92);

  const char *name = 0;
  int codespaces_ok = 0;
  for (u64 i = 0; envp[i]; i++) {
    if (streq(envp[i], env_codespaces)) codespaces_ok = 1;
    if (starts(envp[i], key_name)) name = envp[i] + 15;
  }
  if (!codespaces_ok || !name) xexit(92);
  u64 n = 0;
  if (!valid_name(name, &n)) xexit(92);

  for (u64 i = 0; i < 15; i++) env_name[i] = key_name[i];
  for (u64 i = 0; i < n; i++) env_name[15 + i] = name[i];
  env_name[15 + n] = 0;

  if (xsys3(SYS_close_range, 3, 0xffffffffUL, 0) < 0) xexit(92);
  static const char slash[] = "/";
  if (xsys1(SYS_chdir, (u64)slash) < 0) xexit(92);
  if (!establish_exec_boundary(real_uid)) xexit(92);

  char *clean_env[3];
  clean_env[0] = (char *)env_codespaces;
  clean_env[1] = env_name;
  clean_env[2] = 0;

  char *clean_argv[3];
  clean_argv[0] = (char *)probe_path;
  clean_argv[1] = argc == 2 ? (char *)arg_commit : 0;
  clean_argv[2] = 0;
  xexecve(probe_path, clean_argv, clean_env);
  xexit(92);
}

__attribute__((naked,noreturn,used)) void _start(void) {
  __asm__ volatile(
    "mov %rsp,%rdi\n"
    "andq $-16,%rsp\n"
    "call start_c\n"
  );
  __builtin_unreachable();
}
