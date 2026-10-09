# RPC Evidence: браузерное демо и Cloudflare Free

Публичное демо — статические assets в `web/public`, адрес после публикации
`arc-rpc-evidence.pages.dev`, если имя доступно; фактический URL нужно подтвердить
в dashboard. Python Worker не нужен: Python CLI
сохраняет свою установку, тесты и поведение. Браузер делает ограниченные live
reads прямо к единственному `https://rpc.mainnet.arc.io`; backend proxy нет.
Исходники демо не требуют npm install, компиляции или сторонних runtime scripts.

## Проверки до публикации

Из корня репозитория, Node.js 22 / Python 3.11+:

```sh
npm ci --prefix web --ignore-scripts
npm test --prefix web
python -m web.tests.parity
python -m unittest -v
npx --yes wrangler@4.149.0 deploy --dry-run
```

Parity replay использует результаты существующего Python `demo_report` для всех
12 сценариев и сравнивает request selection/count, verdict, execution, stop reason
и method support. Это offline test, не новое mainnet evidence.
CI также сохраняет прежнюю матрицу Python; новый workflow не делает deploy.
JSDOM — только test dependency: DOM-проверка покрывает ввод, отмену, повторный
запуск и экспорт без сети. Она не проверяет реальный браузерный CORS или layout.
`web/public` не содержит node_modules и не требует установки зависимостей.

## Публикация через dashboard без токена

Убедитесь, что выбран Workers Free в подтверждённом аккаунте.
В Workers & Pages → Pages → Direct Upload создайте `arc-rpc-evidence` через загрузку статических файлов.
Загрузите **содержимое** `web/public`: index.html, app.mjs, evidence.mjs,
json.mjs, style.css и _headers. Не загружайте родительскую папку вместо корня.
Свой домен, backend, secrets, API token, OAuth grant и billing changes не нужны.
Проверьте корневую страницу и response headers после deploy.

Если у владельца уже есть разрешённая Wrangler-авторизация, Pages deployment
использует `npx --yes wrangler@4.149.0 pages deploy web/public --project-name arc-rpc-evidence`.
Команда `npx --yes wrangler@4.149.0 deploy` и корневой `wrangler.json` — отдельная
альтернатива Workers Static Assets с адресом workers.dev; это не Pages deployment.
Dry run выше проверяет только эту альтернативную Workers-конфигурацию.
Эти команды не должны использоваться для создания новых credentials.
[Pages Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/).
[Static assets billing](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/).

## Пройти демо

Нажмите Read live evidence с Block number=0. Сначала проверяется chain 5042,
затем head и pinned number/hash, затем выбранный header.
Для receipt выберите Transaction hash и вставьте уже существующий публичный hash
Arc mainnet. Не создавайте перевод ради проверки. После окончания прочтите target,
chain/head, execution и stop reason; скачайте JSON/Markdown. Cancel сохраняет
частичный отчёт. При неверном вводе прежний отчёт остаётся доступным.

Синтетических подмен live-ответов в UI нет. Страница не выполняет запросы до клика.
CORS/network failure отображается как недостаточное evidence. Provider 429 не
повторяется. Единственный retry — -32014 near-tip; pinned near-tip disagreement
получает один bounded repeat, как в CLI. Все attempts входят в budget.

## Диагностика и явные отличия CLI

Успешный/failed execution выдаётся только при согласии transaction, receipt,
pinned block hash/number/timestamp/list и inclusion at transactionIndex.
Null означает observed-null, без утверждения отсутствия/pruning/failed execution.
Malformed, timeout, wrong identity, incomplete coverage и exhausted budget не
превращаются в verified. Источником остаётся один provider; trust/finality proof нет.

Ограничения браузера:

- Один transaction или числовой block; block hash targets и три targets остаются в CLI.
- 12 sequential attempts, 5 s/read, 45 s/deadline, 256 KiB/response. HTTP redirects
  запрещены, но fetch не позволяет отличить redirect rejection от другого network error.
- JSON depth до 64; nonfinite и unsafe numeric integers отклоняются целиком,
  чтобы не потерять точность. Протокольные hex quantities считаются через BigInt.
- JSON schema `browser-1` отличается от CLI schema 1: большие header numbers
  записаны как decimal strings, timestamp как hex; local-clock head age/freshness
  не вычисляется. Экспорт браузера не является входным replay форматом CLI.
- Браузер принимает только UTF-8 JSON; Python json.loads также распознаёт некоторые
  другие JSON byte encodings. Для id/error.code оба требуют integer token:
  дробная/экспоненциальная запись вроде 1.0 и 1e0 не принимается.
- Browser fetch использует сетевую конфигурацию браузера/ОС; CLI отключает
  environment proxies. Нельзя утверждать одинаковый сетевой маршрут.
- Если deadline и budget заканчиваются одновременно, браузер указывает deadline,
  CLI — request-budget. Это не меняет количество разрешённых попыток или verdict.
  Приостановка вкладки/ОС может задержать таймеры и окончание браузерного запроса.
- Нет фонового монитора, uptime/ranking, archive-state completeness, quorum или chain scan.

## Приватность и проверка деплоя

В DevTools проверьте CSP с connect-src только self и официальный RPC,
nosniff, no-referrer и no-store. Публичный RPC видит IP браузера и targets;
Cloudflare получает page/asset requests и сетевые метаданные.
Демо не отправляет targets на Cloudflare API и ничего не сохраняет автоматически.
JSON содержит raw provider fields, включая публичные адреса/logs/calldata,
если они были возвращены. Экспортируйте и передавайте его осознанно.

Сделайте smoke genesis и одного уже известного успешного receipt; проверьте
actual request count и raw timestamps. Повторите UI сценарий с отменой.
Ошибка CORS не оправдывает добавление arbitrary URL или server proxy.
Для локальной приватности и полного набора targets используйте Python CLI.

Откат — предыдущая проверенная deployment version или удаление только
Pages project arc-rpc-evidence. Отдельной базы и пользовательского хранилища нет.
