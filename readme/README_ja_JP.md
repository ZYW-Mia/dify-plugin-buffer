# Buffer for Dify

コミュニティ開発者 **TenTen** がメンテナンスするDifyツールプラグインです。BufferのGraphQL APIを使い、接続済みアカウントの取得、下書き作成、投稿予約、投稿管理を行います。

[English](../README.md) · [简体中文](README_zh_Hans.md) · 日本語

ツール名、パラメーター、ヘルプ、認証項目は英語・簡体字中国語・日本語に対応し、Difyの表示言語に従います。ツール識別子とAPIの列挙値は各言語で共通です。

## インストールと認証

Dify 1.9.0以降が必要です。[GitHub Releases](https://github.com/ZYW-Mia/dify-plugin-buffer/releases/tag/v0.1.0)から `buffer-0.1.0.difypkg` をダウンロードし、Difyのプラグイン画面でローカルパッケージからインストールしてください。この開発用パッケージは未署名のため、インストール可否はDifyインスタンスの検証ポリシーによります。

作者の名前空間は `TenTen/buffer` です。以前の作者名のパッケージから移行する場合は、新しいパッケージをインストールしてBufferを再認証し、対応するWorkflowテンプレートをインポートしてください。

OAuthを利用する場合：

1. [Buffer Settings → API → App Clients](https://publish.buffer.com/settings/api)で非公開（confidential）のアプリクライアントを作成します。
2. `account:read`、`posts:read`、`posts:write`、`offline_access` を有効にします。
3. DifyのBuffer OAuthクライアント設定に表示される**実際のコールバックURL**をコピーし、そのままBufferのRedirect URIsに登録します。Bufferはローカル開発でもHTTPSを要求します。
4. Client IDとClient SecretをDifyに入力し、認証ボタンからBufferへのアクセスを許可します。

OAuthクライアントはDifyインスタンスごとに設定が必要です。パッケージのインストールだけでは、Bufferアプリの作成やDify Cloudの共有OAuth設定は行われません。個人用ワークフローでは、[Buffer API設定](https://publish.buffer.com/settings/api)で作成した個人用APIキーも利用できます。

## 8つのツール

| ツール | 用途 |
| --- | --- |
| `list_organizations` | アカウントから利用可能な組織を取得します。 |
| `list_channels` | 接続済みアカウント、ID、プラットフォーム、タイムゾーン、接続状態を取得します。 |
| `create_post` | 新規投稿を作成します。初期設定では未公開の下書きとして保存します。 |
| `schedule_post` | 新しい予約投稿を作成するか、キューに追加します。 |
| `list_posts` | 組織、アカウント、状態、期間で投稿を検索します。カーソルによるページ送りに対応します。 |
| `get_post` | 投稿状態、公開URL、公開エラーを取得します。 |
| `update_post` | 下書きや予約投稿を編集し、既存の下書きを予約投稿に変更します。 |
| `delete_post` | Buffer上の投稿を完全に削除するか、予約を取り消します。 |

書き込み操作は1回につき1アカウントを対象とします。複数アカウントへの投稿はWorkflowで繰り返し呼び出してください。各ツールはJSONと、`post_id`、`status` など後続ノードから参照できる出力変数を返します。

## 投稿方法

`create_post` は初期設定で `draft` です。`addToQueue` は次の空き枠、`shareNext` はキューの先頭、`shareNow` は即時公開です。`notification` では通知後に利用者が公開操作を完了する必要があります。

既存の下書きを予約するには、重複作成を避けるため `update_post` を使用します。

```json
{
  "post_id": "EXISTING_DRAFT_ID",
  "mode": "customScheduled",
  "due_at": "2026-11-01T19:00:00+09:00"
}
```

日時は未来で、タイムゾーンの指定が必要です。上の日時はUTCの `2026-11-01T10:00:00.000Z` に変換されます。新規の予約投稿には `schedule_post` を使用します。キュー操作では `due_at` を指定しません。

`update_post` の初期値 `mode=keep` は既存の予約を維持します。省略した画像やタグは保持され、JSONの `[]` を渡すと削除されます。空の任意テキストは無視され、本文を明示的に消す場合は `clear_text=true` を使用します。

## 画像・動画とプラットフォーム設定

`assets_json` にはBufferの添付配列をJSON文字列として指定します。

```json
[{"image":{"url":"https://your-public-host.example/image.png","metadata":{"altText":"画像の説明"}}}]
```

メディアにはBufferと投稿先が取得できる公開HTTP(S) URLが必要です。プラグインはDifyファイルをアップロードしたり、メディアをホストしたりしません。ローカルパス、DifyファイルID、非公開の添付URLは使用できません。動画は `video`、ドキュメントは `document` を指定し、ドキュメントには `title` と `thumbnailUrl` も必要です。

`metadata_json` は投稿先サービス用の `PostInputMetaData` オブジェクトです。Instagramの例：

```json
{"instagram":{"type":"post","shouldShareToFeed":true}}
```

スレッド、最初のコメント、Reels、Pinterestボードなどの設定は[公式APIリファレンス](https://developers.buffer.com/reference.html)を参照してください。各プラットフォームの必須項目や公開制限はBufferが検証します。

## Workflowテンプレート

リポジトリには英語の [Dify Content to Bufferテンプレート](https://github.com/ZYW-Mia/dify-plugin-buffer/blob/main/examples/README.md)もあります。Original ContentまたはAI Assistantで素材を用意し、任意で画像を添付します。Human Inputで内容を確認・編集してから、接続済みアカウントと公開方法を選択します。Maximum charactersは任意で、空欄なら生成時の文字数上限を設定しません。

テンプレートはX、Bluesky、LinkedInの下書き、キュー、予約、即時公開に対応します。投稿先の公開制限や必要なメディアは、Bufferと接続済みアカウントによって異なります。

## エラーと検証状況

HTTP、GraphQL、投稿操作のエラーはDifyのツールエラーとして返されます。書き込みは自動再試行しません。タイムアウト時には既に投稿が作成されている可能性があるため、`list_posts` や `get_post` で確認してから再試行してください。`delete_post` はBuffer上の投稿を削除しますが、投稿先SNSで既に公開された内容の削除を保証しません。

SDKによる全8ツールの読み込みと、OAuth、入力検証、ページ送り、予約日時、エラー処理の自動テストを実施しています。Dify Cloudでは実際の組織と接続済みアカウントを取得できています。現在の **TenTen 0.1.0** 名前空間では、新規インストール、OAuth再認証、実際の書き込み操作の再検証が必要です。[統合チェックリスト](../docs/integration-checklist.md)を参照してください。

OAuthの更新トークンは使用ごとにローテーションします。複数のプラグインプロセス間での同時更新には、ホスト側の調整が必要です。詳細は[OAuth実装メモ](../docs/oauth.md)を参照してください。投稿分析は現行APIで個人用APIキーに制限されるため、このOAuthプラグインには含まれません。

## ソース・サポート・ライセンス

ソースコード：[ZYW-Mia/dify-plugin-buffer](https://github.com/ZYW-Mia/dify-plugin-buffer)。不具合や質問は [GitHub Issues](https://github.com/ZYW-Mia/dify-plugin-buffer/issues)へお願いします。トークン、クライアントシークレット、非公開の投稿内容は公開しないでください。

MITライセンスです。[LICENSE](../LICENSE)と[プライバシーポリシー](../PRIVACY.md)をご確認ください。これは独立したコミュニティ製の連携であり、Buffer公式製品ではありません。
