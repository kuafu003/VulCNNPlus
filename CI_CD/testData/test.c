#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define USERNAME_MAX 32
#define EMAIL_MAX    64
#define NOTE_MAX     128
#define LOG_BUF      256

typedef struct User {
    int id;
    char username[USERNAME_MAX];
    char email[EMAIL_MAX];
    char *note;
    size_t note_len;
} User;

typedef struct Request {
    char raw_name[64];
    char raw_email[128];
    char raw_note[256];
    int want_admin;
} Request;

static void write_log(const char *tag, const char *msg) {
    char buffer[LOG_BUF];

    /* 教学说明：
       危险模式示例通常是：
       - 直接 sprintf / strcat 到固定长度缓冲区
       - 把外部输入直接当格式串
       这里用 snprintf 做安全替代。 */
    snprintf(buffer, sizeof(buffer), "[%s] %s", tag, msg);
    puts(buffer);
}

static int validate_email(const char *email) {
    const char *at = strchr(email, '@');
    const char *dot = strrchr(email, '.');

    if (email == NULL) return 0;
    if (at == NULL || dot == NULL) return 0;
    if (at > dot) return 0;
    if (strlen(email) >= EMAIL_MAX) return 0;
    return 1;
}

static int copy_bounded(char *dst, size_t dst_size, const char *src) {
    if (dst == NULL || src == NULL || dst_size == 0) {
        return -1;
    }

    size_t len = strlen(src);

    /* 教学说明：
       经典风险点 1：拷贝前未检查长度，可能导致缓冲区溢出。
       这里明确进行边界检查。 */
    if (len >= dst_size) {
        return -1;
    }

    memcpy(dst, src, len + 1);
    return 0;
}

static User *alloc_user(void) {
    User *u = (User *)calloc(1, sizeof(User));
    if (!u) {
        write_log("ERROR", "calloc for User failed");
        return NULL;
    }

    u->id = -1;
    u->note = NULL;
    u->note_len = 0;
    return u;
}

static int set_note(User *u, const char *note) {
    if (u == NULL || note == NULL) {
        return -1;
    }

    size_t len = strlen(note);

    /* 教学说明：
       经典风险点 2：长度计算后直接 malloc(len) 而不是 len+1，
       或者整数溢出后分配过小空间。
       这里做了安全写法。 */
    if (len >= NOTE_MAX) {
        return -1;
    }

    char *buf = (char *)malloc(len + 1);
    if (!buf) {
        return -1;
    }

    memcpy(buf, note, len + 1);

    /* 教学说明：
       经典风险点 3：内存泄漏 / double free / use-after-free。
       这里先释放旧指针，再原子性替换。 */
    free(u->note);
    u->note = buf;
    u->note_len = len;
    return 0;
}

static int parse_request(Request *req, const char *input_name,
                         const char *input_email,
                         const char *input_note,
                         int want_admin) {
    if (!req || !input_name || !input_email || !input_note) {
        return -1;
    }

    memset(req, 0, sizeof(*req));

    if (copy_bounded(req->raw_name, sizeof(req->raw_name), input_name) != 0) {
        write_log("WARN", "name too long");
        return -1;
    }

    if (copy_bounded(req->raw_email, sizeof(req->raw_email), input_email) != 0) {
        write_log("WARN", "email too long");
        return -1;
    }

    if (copy_bounded(req->raw_note, sizeof(req->raw_note), input_note) != 0) {
        write_log("WARN", "note too long");
        return -1;
    }

    req->want_admin = want_admin;
    return 0;
}

static int create_user_from_request(User **out_user, const Request *req) {
    if (out_user == NULL || req == NULL) {
        return -1;
    }

    if (!validate_email(req->raw_email)) {
        write_log("WARN", "invalid email");
        return -1;
    }

    User *u = alloc_user();
    if (!u) {
        return -1;
    }

    if (copy_bounded(u->username, sizeof(u->username), req->raw_name) != 0) {
        write_log("WARN", "username rejected");
        free(u);
        return -1;
    }

    if (copy_bounded(u->email, sizeof(u->email), req->raw_email) != 0) {
        write_log("WARN", "email rejected");
        free(u);
        return -1;
    }

    if (set_note(u, req->raw_note) != 0) {
        write_log("WARN", "note rejected");
        free(u);
        return -1;
    }

    /* 教学说明：
       经典风险点 4：权限绕过。
       例如仅依赖客户端传来的 want_admin 字段。
       这里没有真的授予权限，只做日志提醒。 */
    if (req->want_admin) {
        write_log("AUDIT", "admin request ignored by policy");
    }

    u->id = 1001;
    *out_user = u;
    return 0;
}

static void dump_user(const User *u) {
    if (!u) return;

    printf("User{id=%d, username=%s, email=%s, note_len=%zu}\n",
           u->id, u->username, u->email, u->note_len);

    if (u->note) {
        printf("note: %s\n", u->note);
    }
}

static void free_user(User *u) {
    if (!u) return;

    /* 教学说明：
       经典风险点 5：free 后继续访问成员，形成 UAF。
       正确做法是释放后不再使用该对象。 */
    free(u->note);
    u->note = NULL;
    u->note_len = 0;

    free(u);
}

int main(void) {
    Request req;
    User *user = NULL;

    const char *name = "alice_dev";
    const char *email = "alice@example.com";
    const char *note =
        "This is a longer note used for static-analysis teaching. "
        "It exercises heap allocation, bounded copy, logging, validation, "
        "conditional branches, and pointer lifecycle management.";

    if (parse_request(&req, name, email, note, 1) != 0) {
        write_log("ERROR", "failed to parse request");
        return 1;
    }

    if (create_user_from_request(&user, &req) != 0) {
        write_log("ERROR", "failed to create user");
        return 1;
    }

    dump_user(user);
    free_user(user);
    return 0;
}