package main

import (
	"bufio"
	"bytes"
	"crypto/sha256"
	"crypto/tls"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"time"
)

const runtimePath = "/opt/multiverse/v36/runtime.py"
const manifestPath = "/opt/multiverse/v36/closure-manifest.json"
const pythonPath = "/usr/bin/python3"
const triggerPath = "/usr/local/bin/multiverse-v36-trigger"
const controlPath = "/usr/local/sbin/multiverse-v36-control"
const bindingPath = "/opt/multiverse/v36/step3-binding.json"
const step3Path = "/opt/multiverse/v36/step3.py"
const socketPath = "/run/multiverse-v36-anchor.sock"
const receiptRoot = "/dev/shm/multiverse-r1-stage1-phase-c-v19-7-36-v6-receipts"
const mainWant = "5c1403c1f5aabb80d29e8c868440aede8888ce61"
const treeWant = "3d47741b4863411e5c36cb4c28925ac455ab6441"
const step3BlobWant = "1e6584749d99bc15d9e7147ecda2523a821dbd72"
const step3SHAWant = "3b2b1e30ac41770c7cfa6294bf2c6e646e23155688af480a0e996a43060376e1"
const step3SizeWant int64 = 1197
const tmpfsMagic = 0x01021994

type Obj struct {
	Path   string `json:"path"`
	Type   string `json:"type"`
	Target string `json:"target"`
	SHA256 string `json:"sha256"`
	Uid    int    `json:"uid"`
	Gid    int    `json:"gid"`
	Mode   int    `json:"mode"`
	Size   int64  `json:"size"`
}
type Manifest struct {
	Version string         `json:"version"`
	Objects []Obj          `json:"objects"`
	Policy  map[string]any `json:"policy"`
}
type Row struct {
	State    string `json:"state"`
	Evidence string `json:"evidence"`
}

func die(s string) { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V6_PRODUCER_DENIED:"+s); os.Exit(92) }
func uid(fi os.FileInfo) (uint32, error) {
	s, ok := fi.Sys().(*syscall.Stat_t)
	if !ok {
		return 0, errors.New("stat")
	}
	return s.Uid, nil
}
func rootChain(p string) error {
	r, e := filepath.EvalSymlinks(p)
	if e != nil {
		return e
	}
	for q := r; ; q = filepath.Dir(q) {
		fi, e := os.Lstat(q)
		if e != nil {
			return e
		}
		u, e := uid(fi)
		if e != nil || u != 0 || fi.Mode().Perm()&0022 != 0 {
			return fmt.Errorf("class-c:%s", q)
		}
		if q == "/" {
			break
		}
	}
	return nil
}
func hashFile(p string) (int64, string, error) {
	f, e := os.Open(p)
	if e != nil {
		return 0, "", e
	}
	defer f.Close()
	h := sha256.New()
	n, e := io.Copy(h, f)
	return n, hex.EncodeToString(h.Sum(nil)), e
}
func openC(p string) (*os.File, error) {
	r, e := filepath.EvalSymlinks(p)
	if e != nil {
		return nil, e
	}
	if e = rootChain(r); e != nil {
		return nil, e
	}
	fi, e := os.Stat(r)
	if e != nil {
		return nil, e
	}
	u, e := uid(fi)
	if e != nil || u != 0 || fi.Mode().Perm()&0022 != 0 || !fi.Mode().IsRegular() {
		return nil, errors.New("class-c-file")
	}
	return os.Open(r)
}
func loadManifest() (*Manifest, *os.File, error) {
	f, e := openC(manifestPath)
	if e != nil {
		return nil, nil, e
	}
	b, e := io.ReadAll(io.LimitReader(f, 128<<20))
	if e != nil {
		f.Close()
		return nil, nil, e
	}
	if _, e = f.Seek(0, 0); e != nil {
		f.Close()
		return nil, nil, e
	}
	var m Manifest
	if json.Unmarshal(b, &m) != nil || m.Version != "V19.7.36-v6" {
		f.Close()
		return nil, nil, errors.New("manifest")
	}
	return &m, f, nil
}
func verifyManifest(m *Manifest) error {
	for _, o := range m.Objects {
		if !strings.HasPrefix(o.Path, "/") {
			return errors.New("relative")
		}
		fi, e := os.Lstat(o.Path)
		if e != nil {
			return e
		}
		u, e := uid(fi)
		if e != nil || int(u) != o.Uid || o.Uid != 0 || int(fi.Mode().Perm()) != o.Mode {
			return fmt.Errorf("meta:%s", o.Path)
		}
		switch o.Type {
		case "file":
			if e = rootChain(o.Path); e != nil {
				return e
			}
			n, h, e := hashFile(o.Path)
			if e != nil || n != o.Size || h != o.SHA256 {
				return fmt.Errorf("hash:%s", o.Path)
			}
		case "symlink":
			t, e := os.Readlink(o.Path)
			if e != nil || t != o.Target {
				return fmt.Errorf("link:%s", o.Path)
			}
			r, e := filepath.EvalSymlinks(o.Path)
			if e != nil {
				return e
			}
			found := false
			for _, x := range m.Objects {
				if x.Path == r && x.Type == "file" {
					found = true
					break
				}
			}
			if !found {
				if s, e := os.Stat(r); e == nil && s.IsDir() {
					found = true
				}
			}
			if !found {
				return fmt.Errorf("resolved-target-unmanifested:%s", o.Path)
			}
		case "dir":
			if !fi.IsDir() {
				return fmt.Errorf("dir:%s", o.Path)
			}
		default:
			return fmt.Errorf("type:%s", o.Path)
		}
	}
	return nil
}
func statusGate() error {
	b, e := os.ReadFile("/proc/self/status")
	if e != nil {
		return e
	}
	s := string(b)
	if !strings.Contains(s, "NoNewPrivs:\t1") {
		return errors.New("nonewprivs")
	}
	get := func(k string) (uint64, error) {
		for _, l := range strings.Split(s, "\n") {
			if strings.HasPrefix(l, k+":") {
				return strconv.ParseUint(strings.TrimSpace(strings.TrimPrefix(l, k+":")), 16, 64)
			}
		}
		return 0, errors.New(k)
	}
	eff, _ := get("CapEff")
	bnd, _ := get("CapBnd")
	allowed := uint64((1 << 0) | (1 << 6) | (1 << 7))
	if eff&^allowed != 0 || bnd&^allowed != 0 || eff&(1<<21) != 0 || bnd&(1<<21) != 0 {
		return errors.New("caps")
	}
	return nil
}
func mountGate() error {
	b, e := os.ReadFile("/proc/self/mountinfo")
	if e != nil {
		return e
	}
	trusted := []string{"/usr", "/bin", "/lib", "/etc/ssl", "/opt/multiverse"}
	for _, l := range strings.Split(string(b), "\n") {
		f := strings.Fields(l)
		if len(f) < 6 {
			continue
		}
		mp := strings.ReplaceAll(f[4], "\\040", " ")
		if mp == "/" {
			continue
		}
		for _, t := range trusted {
			if mp == t || strings.HasPrefix(mp, t+"/") {
				return fmt.Errorf("mount-overlay:%s", mp)
			}
		}
	}
	return nil
}
func shmGate() error {
	var s syscall.Statfs_t
	if syscall.Statfs("/dev/shm", &s) != nil || uint64(s.Type) != tmpfsMagic {
		return errors.New("shm")
	}
	return nil
}
func zeroSwap() bool {
	b, e := os.ReadFile("/proc/swaps")
	return e == nil && len(strings.Split(strings.TrimSpace(string(b)), "\n")) <= 1
}
func strongReceipt(b []byte) error {
	if e := shmGate(); e != nil {
		return e
	}
	if _, e := os.Lstat(receiptRoot); !os.IsNotExist(e) {
		return errors.New("receipt-preexists")
	}
	if e := os.Mkdir(receiptRoot, 0700); e != nil {
		return e
	}
	d, e := os.Open(receiptRoot)
	if e != nil {
		return e
	}
	defer d.Close()
	fd, e := syscall.Openat(int(d.Fd()), "PRE_PYTHON.json", syscall.O_RDWR|syscall.O_CREAT|syscall.O_EXCL|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0400)
	if e != nil {
		return e
	}
	f := os.NewFile(uintptr(fd), "receipt")
	defer f.Close()
	if _, e = f.Write(b); e != nil {
		return e
	}
	if e = f.Sync(); e != nil {
		return e
	}
	if _, e = f.Seek(0, 0); e != nil {
		return e
	}
	g, e := io.ReadAll(f)
	if e != nil || string(g) != string(b) {
		return errors.New("receipt-readback")
	}
	return d.Sync()
}
func freshMain() error {
	tr := &http.Transport{Proxy: nil, TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS12}}
	cl := &http.Client{Transport: tr, Timeout: 10 * time.Second, CheckRedirect: func(r *http.Request, v []*http.Request) error { return http.ErrUseLastResponse }}
	get := func(u string, v any) error {
		r, e := http.NewRequest("GET", u, nil)
		if e != nil {
			return e
		}
		r.Header.Set("Accept", "application/vnd.github+json")
		x, e := cl.Do(r)
		if e != nil {
			return e
		}
		defer x.Body.Close()
		if x.StatusCode != 200 {
			return fmt.Errorf("http:%d", x.StatusCode)
		}
		return json.NewDecoder(io.LimitReader(x.Body, 1<<20)).Decode(v)
	}
	var ref struct {
		Object struct {
			SHA string `json:"sha"`
		} `json:"object"`
	}
	if e := get("https://api.github.com/repos/fufufu1116/multiverse-research/git/ref/heads/main", &ref); e != nil {
		return e
	}
	if ref.Object.SHA != mainWant {
		return errors.New("main-drift")
	}
	var c struct {
		Tree struct {
			SHA string `json:"sha"`
		} `json:"tree"`
}
	if e := get("https://api.github.com/repos/fufufu1116/multiverse-research/git/commits/"+ref.Object.SHA, &c); e != nil {
		return e
	}
	if c.Tree.SHA != treeWant {
		return errors.New("tree-drift")
	}
	return nil
}
func cleanEnv(c, n string) []string {
	return []string{"CODESPACES=" + c, "CODESPACE_NAME=" + n, "LANG=C", "LC_ALL=C", "PATH=/usr/bin:/bin", "HOME=/nonexistent", "XDG_CONFIG_HOME=/opt/multiverse/v36/empty-config", "GIT_CONFIG_NOSYSTEM=1", "GIT_CONFIG_GLOBAL=/dev/null", "GIT_CONFIG_SYSTEM=/dev/null", "GIT_TERMINAL_PROMPT=0", "GIT_ASKPASS=/bin/false", "SSH_ASKPASS=/bin/false", "GH_CONFIG_DIR=/opt/multiverse/v36/empty-config", "GH_BROWSER=/bin/false", "GH_PAGER=cat"}
}
func rows() map[string]Row {
	m := map[string]Row{}
	p := func(i int, e string) { m[strconv.Itoa(i)] = Row{"PASS", e}}
	p(1, "Codespaces identity captured before clearenv")
	p(2, "static root-image producer linux/amd64")
	p(3, "zero swap mechanically checked")
	p(4, "/dev/shm tmpfs mechanically checked")
	p(5, "/proc/self/fd same-object execution available")
	p(6, "trigger peer executable dev+ino must equal root-owned frozen trigger object")
	p(7, "recursive symlink target plus ELF/library/stdlib/native closure manifest and build actual-use selftest")
	p(8, "clear environment before dynamic child; fixed child environment")
	p(9, "Python executable once-opened after Class-C realpath resolution and executed through inherited fd")
	p(10, "PyNaCl 1.6.2 roundtrip plus mapped/module identity in runtime")
	p(11, "root-only frozen control runner implements exact fd-bound git/gh/browser successor actions with allowlisted argv/env/config/host/endpoints")
	p(12, "Fresh GitHub main ref and commit-tree proof by static producer")
	p(13, "exact Step3 path/blob/SHA256/size/mode bound and same-object loader contract verified")
	m["14"] = Row{"POST_OAUTH_ONLY", "credential-dependent identity/scope/ruleset/fence/environment proof remains post OAuth"}
	p(15, "pre-Python dirfd O_EXCL O_NOFOLLOW tmpfs receipt fsync/readback")
	p(16, "Class-C ownership/mode plus no SYS_ADMIN and mount overlay gate")
	return m
}
func peerIsTrigger(pid int32) bool {
	a, e := os.Stat(fmt.Sprintf("/proc/%d/exe", pid))
	if e != nil {
		return false
	}
	b, e := os.Stat(triggerPath)
	if e != nil {
		return false
	}
	sa, oka := a.Sys().(*syscall.Stat_t)
	sb, okb := b.Sys().(*syscall.Stat_t)
	if !oka || !okb {
		return false
	}
	u, _ := uid(b)
	return u == 0 && b.Mode().Perm()&0022 == 0 && sa.Dev == sb.Dev && sa.Ino == sb.Ino
}
func verifyStep3Opened(sf *os.File) error {
	if _, e := sf.Seek(0, 0); e != nil {
		return e
	}
	h := sha256.New()
	n, e := io.Copy(h, sf)
	if e != nil {
		return e
	}
	if n != step3SizeWant || hex.EncodeToString(h.Sum(nil)) != step3SHAWant {
		return errors.New("step3-opened-identity")
	}
	if _, e = sf.Seek(0, 0); e != nil {
		return e
	}
	bf, e := openC(bindingPath)
	if e != nil {
		return e
	}
	defer bf.Close()
	bb, e := io.ReadAll(io.LimitReader(bf, 1<<20))
	if e != nil {
		return e
	}
	var q struct {
		Version string `json:"version"`
		Step3   struct {
			Path, GitBlob, SHA256, Mode string
			Size                        int64
			Mutations                   int
		} `json:"step3"`
	}
	if json.Unmarshal(bb, &q) != nil || q.Version != "V19.7.36-v6" || q.Step3.Path != step3Dath || q.Step3.GitBlob != step3BlobWant || q.Step3.SHA256 != step3SHAWant ||Ä¹MÑ•ÀÌ¹M¥é”€„ôÍÑ•ÀÍM¥é•]…¹ÐñðÄ¹MÑ•ÀÌ¹5½‘”€„ô€‰9=95UQQ%9ˆñðÄ¹MÑ•ÀÌ¹5ÕÑ…Ñ¥½¹Ì€„ô€Àì($%É•ÑÕÉ¸•ÉÉ½ÉÌ¹9•Ü ‰ÍÑ•ÀÌµ‰¥¹‘¥¹œˆ¤(%ô(%É•ÑÕÉ¸¹¥°)ô()™Õ¹ŒÉÕ¹½¹ÑÉ½±MÑ•ÀÌ¡½‘•ÍÁ…•Ì°¹…µ”ÍÑÉ¥¹œ¤€¡mu‰åÑ”°•ÉÉ½È¤ì(%˜°”€èô½Á•¹¡½¹ÑÉ½±A…Ñ ¤(%¥˜”€„ô¹¥°ì($%É•ÑÕÉ¸¹¥°°”(%ô(%‘•™•È˜¹±½Í” ¤(%µ€èô•á•Œ¹½µµ…¹ ˆ½ÁÉ½Œ½Í•±˜½™¼Ìˆ°€‰ÍÑ•ÀÌµÁÉ•™±¥¡Ðˆ¤(%µ¹áÑÉ…¥±•Ì€ômt©½Ì¹¥±•í™ô(%µ¹¹Ø€ô±•…¹¹Ø¡½‘•ÍÁ…•Ì°¹…µ”¤(%Ù…È½ÕÐ°•È‰åÑ•Ì¹	Õ™™•È(%µ¹MÑ‘½ÕÐ€ô€™½ÕÐ(%µ¹MÑ‘•ÉÈ€ô€™•È(%”€ôµ¹IÕ¸ ¤(%¥˜”€„ô¹¥°ì($%É•ÑÕÉ¸¹¥°°™µÐ¹ÉÉ½É˜ ‰½¹ÑÉ½°µÍÑ•ÀÌè•Üè•Ìˆ°”°ÍÑÉ¥¹Ì¹QÉ¥µMÁ…”¡•È¹MÑÉ¥¹œ ¤¤¤(%ô(%¥˜½ÕÐ¹1•¸ ¤€ø€ÄððÈÀì($%É•ÑÕÉ¸¹¥°°•ÉÉ½ÉÌ¹9•Ü ‰½¹ÑÉ½°µÍÑ•ÀÌµ½ÕÑÁÕÐµ±…É”ˆ¤(%ô(%Ù…ÈÈµ…ÁmÍÑÉ¥¹u…¹ä(%¥˜©Í½¸¹U¹µ…ÉÍ¡…°¡½ÕÐ¹	åÑ•Ì ¤°€™È¤€„ô¹¥°ñðÉl‰Ù•ÉÍ¥½¸‰t€„ô€‰XÄä¸Ü¸ÌØµØØˆñðÉl‰…Ñ¥½¸‰t€„ô€‰MQ@Í}9=95UQQ%9}AI1%!PˆñðÉl‰µÕÑ…Ñ¥½¹Ì‰t€„ô™±½…ÐØÐ À¤ì($%É•ÑÕÉ¸¹¥°°•ÉÉ½ÉÌ¹9•Ü ‰½¹ÑÉ½°µÍÑ•ÀÌµÍ¡•µ„ˆ¤(%ô(%É•ÑÕÉ¸½ÕÐ¹	åÑ•Ì ¤°¹¥°)ô()™Õ¹ŒÉÕ¹MÑ•ÀÍM…µ•=‰©•Ð¡½‘•ÍÁ…•Ì°¹…µ”ÍÑÉ¥¹œ¤•ÉÉ½Èì(%Áä°”€èô½Á•¹¡ÁåÑ¡½¹A…Ñ ¤(%¥˜”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%‘•™•ÈÁä¹±½Í” ¤(%Í˜°”€èô½Á•¹¡ÍÑ•ÀÍA…Ñ ¤(%¥˜”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%‘•™•ÈÍ˜¹±½Í” ¤(%¥˜”€ôÙ•É¥™åMÑ•ÀÍ=Á•¹•¡Í˜¤ì”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%Á…¥È°”€èôÍåÍ…±°¹M½­•ÑÁ…¥È¡ÍåÍ…±°¹}U9%`°ÍåÍ…±°¹M=-}MQI5ñÍåÍ…±°¹M=-}1=a°€À¤(%¥˜”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%Á…É•¹Ð€èô½Ì¹9•Ý¥±”¡Õ¥¹ÑÁÑÈ¡Á…¥ÉlÁt¤°€‰ÍÑ•ÀÌµÁ…É•¹Ðˆ¤(%¡¥±€èô½Ì¹9•Ý¥±”¡Õ¥¹ÑÁÑÈ¡Á…¥ÉlÅt¤°€‰ÍÑ•ÀÌµ¡¥±ˆ¤(%‘•™•ÈÁ…É•¹Ð¹±½Í” ¤(%‘•™•È¡¥±¹±½Í” ¤(%½‘”€èô€‰¥µÁ½ÉÐ½Ìí™õ¥¹Ð¡½Ì¹•¹Ù¥É½¹l5U1Q%YIM}XÌÙ}XÙ}MQ@Í}t¤í¼õmuq¹Ý¡¥±”QÉÕ”éq¸ˆõ½Ì¹É•…¡™°ØÔÔÌØ¥q¸¥˜¹½Ðˆé‰É•…­q¸¼¹…ÁÁ•¹¡ˆ¥q¹•á•Œ¡½µÁ¥±”¡ˆœœ¹©½¥¸¡¼¤°œñØÄä¸Ü¸ÌØµØØµÍÑ•ÀÌøœ°•á•Œœ¤±ì}}¹…µ•}|œè}}µ…¥¹}|ô¤ˆ(%µ€èô•á•Œ¹½µµ…¹ ˆ½ÁÉ½Œ½Í•±˜½™¼Ìˆ°€ˆµ$ˆ°€ˆµLˆ°€ˆµˆ°€ˆµŒˆ°½‘”¤(%µ¹áÑÉ…¥±•Ì€ômt©½Ì¹¥±•íÁä°Í˜°¡¥±‘ô(%µ¹¹Ø€ô…ÁÁ•¹¡±•…¹¹Ø¡½‘•ÍÁ…•Ì°¹…µ”¤°€‰5U1Q%YIM}XÌÙ}XÙ}MQ@Í}ôÐˆ°€‰5U1Q%YIM}XÌÙ}XÙ}=9QI=1}ôÔˆ°€‰5U1Q%YIM}XÌÙ}XÙ}MQ@Í}5=õ9=95UQQ%9ˆ¤(%µ¹MÑ‘½ÕÐ€ô½Ì¹MÑ‘½ÕÐ(%µ¹MÑ‘•ÉÈ€ô½Ì¹MÑ‘•ÉÈ(%µ¹MåÍAÉ½ÑÑÈ€ô€™ÍåÍ…±°¹MåÍAÉ½ÑÑÉíÉ•‘•¹Ñ¥…°è€™ÍåÍ…±°¹É•‘•¹Ñ¥…±íU¥è€ÄÀÀÀ°¥è€ÄÀÀÀ°9½M•ÑÉ½ÕÁÌèÑÉÕ•õô(%¥˜”€ôµ¹MÑ…ÉÐ ¤ì”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%|€ô¡¥±¹±½Í” ¤(%‰È€èô‰Õ™¥¼¹9•ÝI•…‘•È¡¥¼¹1¥µ¥ÑI•…‘•È¡Á…É•¹Ð°€ÔÄÈ¤¤(%É•Ä°”€èô‰È¹I•…‘MÑÉ¥¹œ q¸œ¤(%¥˜”€„ô¹¥°ñðÉ•Ä€„ô€‰íp‰…Ñ¥½¹pˆép‰MQ@Í}9=95UQQ%9}AI1%!Qpˆ±p‰Ù•ÉÍ¥½¹pˆép‰XÄä¸Ü¸ÌØµØÙp‰õq¸ˆì($%|€ôµ¹AÉ½•ÍÌ¹-¥±° ¤($%|€ôµ¹]…¥Ð ¤($%É•ÑÕÉ¸•ÉÉ½ÉÌ¹9•Ü ‰ÍÑ•ÀÌµÉ•ÅÕ•ÍÐˆ¤(%ô(%É•ÍÀ°”€èôÉÕ¹½¹ÑÉ½±MÑ•ÀÌ¡½‘•ÍÁ…•Ì°¹…µ”¤(%¥˜”€„ô¹¥°ì($%|€ôµ¹AÉ½•ÍÌ¹-¥±° ¤($%|€ôµ¹]…¥Ð ¤($%É•ÑÕÉ¸”(%ô(%¥˜|°”€ôÁ…É•¹Ð¹]É¥Ñ”¡É•ÍÀ¤ì”€„ô¹¥°ì($%|€ôµ¹AÉ½•ÍÌ¹-¥±° ¤($%|€ôµ¹]…¥Ð ¤($%É•ÑÕÉ¸”(%ô(%¥˜ÕŒ°½¬€èôÁ…É•¹Ð¹MåÍ…±±½¹¸ ¤ì½¬€ôô¹¥°ì($%|€ôÕŒ¹½¹ÑÉ½°¡™Õ¹Œ¡™Õ¥¹ÑÁÑÈ¤ì|€ôÍåÍ…±°¹M¡ÕÑ‘½Ý¸¡¥¹Ð¡™¤°ÍåÍ…±°¹M!UQ}]H¤ô¤(%ô(%É•ÑÕÉ¸µ¹]…¥Ð ¤)ô()™Õ¹ŒÉÕ¹¡…¥¸¡½‘•ÍÁ…•Ì°¹…µ”ÍÑÉ¥¹œ¤•ÉÉ½Èì(%¥˜”€èôÍÑ…ÑÕÍ…Ñ” ¤ì”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%¥˜”€èôµ½Õ¹Ñ…Ñ” ¤ì”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%¥˜€…é•É½MÝ…À ¤ì($%É•ÑÕÉ¸•ÉÉ½ÉÌ¹9•Ü ‰ÍÝ…Àˆ¤(%ô(%¥˜”€èôÍ¡µ…Ñ” ¤ì”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%´°µ˜°”€èô±½…‘5…¹¥™•ÍÐ ¤(%¥˜”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%‘•™•Èµ˜¹±½Í” ¤(%¥˜”€ôÙ•É¥™å5…¹¥™•ÍÐ¡´¤ì”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%™½È|°À€èôÉ…¹”muÍÑÉ¥¹í½¹ÑÉ½±A…Ñ °‰¥¹‘¥¹A…Ñ °ÍÑ•ÀÍA…Ñ °ÑÉ¥•ÉA…Ñ¡ôì($%¥˜”€ôÉ½½Ñ¡…¥¸¡À¤ì”€„ô¹¥°ì($$%É•ÑÕÉ¸”($%ô(%ô(%¥˜”€ô™É•Í¡5…¥¸ ¤ì”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%Áä°”€èô½Á•¹¡ÁåÑ¡½¹A…Ñ ¤(%¥˜”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%‘•™•ÈÁä¹±½Í” ¤(%ÉÐ°”€èô½Á•¹¡ÉÕ¹Ñ¥µ•A…Ñ ¤(%¥˜”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%‘•™•ÈÉÐ¹±½Í” ¤(%É••¥ÁÐ°|€èô©Í½¸¹5…ÉÍ¡…°¡µ…ÁmÍÑÉ¥¹u…¹åì‰Ù•ÉÍ¥½¸ˆè€‰XÄä¸Ü¸ÌØµØØˆ°€‰ÁÉ•}ÁåÑ¡½¸ˆèÑÉÕ”°€‰µ…¥¸ˆèµ…¥¹]…¹Ð°€‰ÑÉ•”ˆèÑÉ••]…¹Ñô¤(%¥˜”€ôÍÑÉ½¹I••¥ÁÐ¡É••¥ÁÐ¤ì”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%…È°…Ü°”€èô½Ì¹A¥Á” ¤(%¥˜”€„ô¹¥°ì($%É•ÑÕÉ¸”(%ô(%‘•™•È…È¹±½Í” ¤(%„€èôµ…ÁmÍÑÉ¥¹u…¹åì‰Ù•ÉÍ¥½¸ˆè€‰XÄä¸Ü¸ÌØµØØˆ°€‰Í½ÕÉ”ˆè€‰I==Q}%5}9!=I}AI=UI}XØˆ°€‰µ…ÑÉ¥àˆèÉ½ÝÌ ¥ô(%…ˆ°|€èô©Í½¸¹5…ÉÍ¡…°¡„¤(%¼™Õ¹Œ ¤ì‘•™•È…Ü¹±½Í” ¤ì…Ü¹]É¥Ñ”¡…ˆ¤ô ¤(%½‘”€èô€‰¥µÁ½ÉÐ½Ìí™õ¥¹Ð¡½Ì¹•¹Ù¥É½¹l5U1Q%YIM}XÌÙ}XÙ}IU9Q%5}t¤í¼õmuq¹Ý¡¥±”QÉÕ”éq¸ˆõ½Ì¹É•…¡™°ØÔÔÌØ¥q¸¥˜¹½Ðˆé‰É•…­q¸¼¹…ÁÁ•¹¡ˆ¥q¹•á•Œ¡½µÁ¥±”¡ˆœœ¹©½¥¸¡¼¤°œñØÄä¸Ü¸ÌØµØØµÉÕ¹Ñ¥µ”øœ°•á•Œœ¤±ì}}¹…µ•}|œè}}µ…¥¹}|ô¤ˆ(%µ€èô•á•Œ¹½µµ…¹ ˆ½ÁÉ½Œ½Í•±˜½™¼Ìˆ°€ˆµ$ˆ°€ˆµLˆ°€ˆµˆ°€ˆµŒˆ°½‘”¤(%µ¹áÑÉ…¥±•Ì€ômt©½Ì¹¥±•íÁä°ÉÐ°µ˜°…Éô(%µ¹¹Ø€ô…ÁÁ•¹¡±•…¹¹Ø¡½‘•ÍÁ…•Ì°¹…µ”¤°€‰5U1Q%YIM}XÌÙ}XÙ}IU9Q%5}ôÐˆ°€‰5U1Q%YIM}XÌÙ}XÙ}59%MQ}ôÔˆ°€‰5U1Q%YIM}XÌÙ}XÙ}QQMQ}ôØˆ¤(%µ¹MÑ‘½ÕÐ€ô½Ì¹MÑ‘½ÕÐ(%µ¹MÑ‘•ÉÈ€ô½Ì¹MÑ‘•ÉÈ(%µ¹MåÍAÉ½ÑÑÈ€ô€™ÍåÍ…±°¹MåÍAÉ½ÑÑÉíÉ•‘•¹Ñ¥…°è€™ÍåÍ…±°¹É•‘•¹Ñ¥…±íU¥è€ÄÀÀÀ°¥è€ÄÀÀÀ°9½M•ÑÉ½ÕÁÌèÑÉÕ•õô(%”€ôµ¹IÕ¸ ¤(%¥˜à°½¬€èô”¸ ©•á•Œ¹á¥ÑÉÉ½È¤ì½¬€˜˜à¹á¥Ñ½‘” ¤€ôô€äÈì($%É•ÑÕÉ¸¹¥°(%ô(%É•ÑÕÉ¸”)ô)™Õ¹Œµ…¥¸ ¤ì(%¥˜ÉÕ¹Ñ¥µ”¹==L€„ô€‰±¥¹ÕàˆñðÉÕ¹Ñ¥µ”¹=I €„ô€‰…µØÐˆñð½Ì¹•Ñ•Õ¥ ¤€„ô€Àì($%‘¥” ‰A1Q=I4ˆ¤(%ô(%½‘•ÍÁ…•±…œ€èô½Ì¹•Ñ•¹Ø ‰=MALˆ¤(%¸€èô½Ì¹•Ñ•¹Ø ‰=MA}95ˆ¤(%½Ì¹±•…É•¹Ø ¤(%½Ì¹M•Ñ•¹Ø ‰19ˆ°€‰ˆ¤(%½Ì¹M•Ñ•¹Ø ‰1}10ˆ°€‰ˆ¤(%¥˜½‘•ÍÁ…•±…œ€„ô€‰ÑÉÕ”ˆñð¸€ôô€ˆˆì($%‘¥” ‰=MALˆ¤(%ô(%|€ô½Ì¹I•µ½Ù”¡Í½­•ÑA…Ñ ¤(%±¸°”€èô¹•Ð¹1¥ÍÑ•¸ ‰Õ¹¥àˆ°Í½­•ÑA…Ñ ¤(%¥˜”€„ô¹¥°ì($%‘¥” ‰M=-Pˆ¤(%ô(%‘•™•È±¸¹±½Í” ¤(%¥˜”€ô½Ì¹¡½Ý¸¡Í½­•ÑA…Ñ °€ÄÀÀÀ°€ÄÀÀÀ¤ì”€„ô¹¥°ì($%‘¥” ‰M=-Q}!=]8ˆ¤(%ô(%¥˜”€ô½Ì¹¡µ½¡Í½­•ÑA…Ñ °€ÀØÀÀ¤ì”€„ô¹¥°ì($%‘¥” ‰M=-Q}5=ˆ¤(%ô(%™µÐ¹ÁÉ¥¹Ñ±¸¡½Ì¹MÑ‘•ÉÈ°€‰A!M}}XÄå|Ý|ÌÙ}XÙ}I==Q}9!=I}Idˆ¤(%™½Èì($%Œ°”€èô±¸¹•ÁÐ ¤($%¥˜”€„ô¹¥°ì($$%‘¥” ‰APˆ¤($%ô($%™Õ¹Œ ¤ì($$%‘•™•ÈŒ¹±½Í” ¤($$%ÕŒ€èôŒ¸ ©¹•Ð¹U¹¥á½¹¸¤($$%É…Ü°|€èôÕŒ¹MåÍ…±±½¹¸ ¤($$%Ù…ÈÁ••È€©ÍåÍ…±°¹UÉ•($$%É…Ü¹½¹ÑÉ½°¡™Õ¹Œ¡™Õ¥¹ÑÁÑÈ¤ìÁ••È°|€ôÍåÍ…±°¹•ÑÍ½­½ÁÑUÉ•¡¥¹Ð¡™¤°ÍåÍ…±°¹M=1}M=-P°ÍåÍ…±°¹M=}AII¤ô¤($$%¥˜Á••È€ôô¹¥°ñðÁ••È¹U¥€„ô€ÄÀÀÀñð€…Á••É%ÍQÉ¥•È¡Á••È¹A¥¤ì($$$%™µÐ¹ÁÉ¥¹Ñ±¸¡Œ°€‰9%AI}aUQ	1ˆ¤($$$%É•ÑÕÉ¸($$%ô($$%Ì°”€èô‰Õ™¥¼¹9•ÝI•…‘•È¡¥¼¹1¥µ¥ÑI•…‘•È¡Œ°€ØÐ¤¤¹I•…‘MÑÉ¥¹œ q¸œ¤($$%¥˜”€„ô¹¥°ñðÌ€„ô€‰MQIPXÄä¸Ü¸ÌØµØÙq¸ˆì($$$%™µÐ¹ÁÉ¥¹Ñ±¸¡Œ°€‰9%AI=Q==0ˆ¤($$$%É•ÑÕÉ¸($$%ô($$%¥˜”€ôÉÕ¹¡…¥¸¡½‘•ÍÁ…•±…œ°¸¤ì”€„ô¹¥°ì($$$%™µÐ¹ÁÉ¥¹Ñ±¸¡Œ°€‰9%ˆ°”¤($$$%É•ÑÕÉ¸($$%ô($$%™µÐ¹ÁÉ¥¹Ñ±¸¡Œ°€‰IY%]}Ii}IäÉ}=9%I5ˆ¤($%ô ¤(%ô)ô(