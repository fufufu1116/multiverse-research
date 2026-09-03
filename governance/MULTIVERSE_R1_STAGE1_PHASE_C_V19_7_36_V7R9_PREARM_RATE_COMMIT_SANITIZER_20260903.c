#if !defined(__x86_64__)
#error "v7r9 sanitizer requires linux amd64"
#endif

typedef unsigned long u64;
typedef long s64;

static const char probe_path[] = "/usr/local/bin/multiverse-v36-prearm-rate-readiness-v7r9";
static const char env_codespaces[] = "CODESPACES=true";
static const char key_codespaces[] = "CODESPACES=";
static const char key_name[] = "CODESPACE_NAME=";
static const char arg_commit[] = "commit";
static char env_name[15 + 129];

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

static __attribute__((noreturn)) void start_c(u64 *sp) {
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
