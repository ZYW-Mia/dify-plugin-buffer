# Buffer Dify 插件

由社区创作者 **TenTen** 维护。

[English](../README.md) · 简体中文 · [日本語](README_ja_JP.md)

插件名称、工具参数、帮助说明和授权字段支持英文、简体中文和日文，随 Dify 界面语言显示。工具标识和 API 枚举值保持一致。

内部插件标识为 `tenten/buffer`，署名仍为 **TenTen**。Dify 要求内部标识全小写，旧的 `TenTen/buffer` 包因此无法发布到 Marketplace。迁移时请安装并授权小写标识的新包，然后导入配套模板。

通过 Buffer OAuth 2.0 + PKCE 或个人 API Key，在 Dify Agent / Workflow 中查询社交账号、创建草稿、排期和管理帖子。

## 安装和授权

需要 Dify 1.9.0 或更新版本。从 [GitHub Releases](https://github.com/ZYW-Mia/dify-plugin-buffer/releases/tag/v0.1.0) 下载 `buffer-0.1.0.difypkg`，在「插件 → 从本地文件安装」中选择该文件。开发包未签名，是否允许安装取决于实例的插件验证策略。

推荐使用 OAuth：

1. 前往 [Buffer Settings → API → App Clients](https://publish.buffer.com/settings/api)，创建私有（confidential）应用。
2. 开启 `account:read`、`posts:read`、`posts:write` 和 `offline_access`。
3. 在 Dify 的 Buffer OAuth 客户端设置中复制**实际显示的回调 URL**，原样填入 Buffer Redirect URIs。Buffer 要求 HTTPS，本地开发也一样。
4. 将 Client ID 和 Client Secret 填入 Dify，点击授权并在 Buffer 确认。

OAuth 客户端需要由 Dify 实例管理员配置，安装插件不会自动创建 Buffer 应用。个人测试也可以在插件凭证中填写个人 API Key。

## 8 个工具

| 工具 | 用途 |
| --- | --- |
| `list_organizations` | 查询组织并取得 `organization_id` |
| `list_channels` | 查询已连接的账号、平台、时区和连接状态 |
| `create_post` | 创建新帖子，默认仅保存草稿 |
| `schedule_post` | 创建新的定时帖子或加入发布队列 |
| `list_posts` | 按账号、状态和时间查询，支持游标分页 |
| `get_post` | 查询帖子状态、发布时间、链接及失败原因 |
| `update_post` | 编辑草稿或已排期的帖子，也可把已有草稿转为排期 |
| `delete_post` | 永久删除 Buffer 帖子或取消排期 |

每次发帖操作对应一个社交账号。多平台发布请在 Workflow 中对账号逐个调用。每个工具同时输出 JSON 和可直接引用的命名变量，例如 `post_id`、`status`、`posts`、`has_next_page`、`end_cursor`。

## 给 Template 的推荐调用顺序

仓库中的英文 [Workflow 模板](https://github.com/ZYW-Mia/dify-plugin-buffer/blob/main/examples/README.md) 支持：原始内容或 AI 生成素材 → 查询组织和已连接账号 → Human Input 审核内容、选择账号和发布方式 → 执行已确认的 Buffer 操作。开始时可上传一张配图，Maximum characters 留空表示不设置生成字数上限。

如果需要先在 Buffer 保存草稿再审核，可使用 `create_post(mode=draft)` → 人工审核 → `update_post` 排期已有草稿 → `get_post` 查询状态。

用 `update_post` 排期已有草稿可以避免重复创建帖子。示例：

```json
{
  "post_id": "已有草稿ID",
  "mode": "customScheduled",
  "due_at": "2026-11-01T18:00:00+08:00"
}
```

时间必须在未来且包含时区；上面的北京时间会转换为 UTC `2026-11-01T10:00:00.000Z`。`addToQueue` 使用账号下一个队列时段；`shareNext` 插入队首；`shareNow` 会立即发布。选择 `notification` 则只发送提醒，需要人工完成发布。

`update_post` 默认 `mode=keep`，编辑文案时保留原排期。未提供媒体和标签时保留原值，填入 JSON `[]` 可清空。空白的可选文案不作更新；需要清空时显式设置 `clear_text=true`。

## 图片、视频和平台专属配置

`assets_json` 接受以下 JSON 字符串：

```json
[{"image":{"url":"https://你的公开域名/image.png","metadata":{"altText":"图片说明"}}}]
```

媒体需要事先托管在 Buffer 和目标平台可访问的公开 HTTP(S) URL。插件不负责上传 Dify 文件，不能直接使用 Dify 文件 ID、本地路径或私有附件链接。视频使用 `video`；文档使用 `document`，还需 `title` 和 `thumbnailUrl`。

`metadata_json` 接受 Buffer 各平台配置，例如 Instagram 图片帖子：

```json
{"instagram":{"type":"post","shouldShareToFeed":true}}
```

线程、首条评论、Reel、Pinterest Board 等参数以 [Buffer 官方 API Reference](https://developers.buffer.com/reference.html) 为准。各平台的必填内容和发布限制由 Buffer 校验。

## 验证与后续联调

已实现真实 GraphQL 调用、OAuth 授权码交换及 refresh token 轮换，全部工具可由 Dify SDK 加载。自动化测试覆盖参数校验、排期、分页、OAuth、错误处理及模拟完整调用流程。维护者已于 2026 年 10 月 20 日确认完成真实 Dify 安装、Buffer OAuth 授权和真实发帖验证，并确认开发者协议。本次修复仅规范内部作者标识，不改变 Buffer API 行为；重复回归步骤见 [集成检查清单](../docs/integration-checklist.md)。

Buffer API 的分析数据当前仅对个人 API Key 开放，OAuth App Client 无权读取，因此首版没有提供分析工具。请求超时后先查询帖子状态再重试，避免重复发帖。

开发、打包、隐私说明及完整示例见 [英文 README](../README.md)。源码与问题反馈见 [GitHub 仓库](https://github.com/ZYW-Mia/dify-plugin-buffer) 和 [Issues](https://github.com/ZYW-Mia/dify-plugin-buffer/issues)。请勿在公开反馈中附上令牌、客户端密钥或私密帖子内容。
