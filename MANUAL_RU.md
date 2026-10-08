# Arc RPC Evidence: запуск и чтение результата

Инструмент пригодится, когда RPC вернул `null`, receipt расходится с transaction
или исторический блок не находится. Он проверяет несколько конкретных объектов,
сохраняет наблюдения и объясняет, где данных недостаточно для вывода.

Нужны Python 3.11 или новее и Git. Для demo интернет не нужен после скачивания
репозитория. Для live проверки нужен доступ к официальному Arc RPC; API key,
кошелёк и USDC не нужны. Это локальный CLI, сервер не запускается.

## Установка

```console
git clone https://github.com/kuilef/arc-rpc-evidence.git
cd arc-rpc-evidence
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps .
.\.venv\Scripts\arc-rpc-evidence.exe demo --scenario null-receipt --output reports/demo-null
```

Linux/macOS:

```console
.venv/bin/python -m pip install --no-deps .
.venv/bin/arc-rpc-evidence demo --scenario null-receipt --output reports/demo-null
```

Из корня репозитория можно вообще не устанавливать пакет:

```console
python -m arc_rpc_evidence demo --scenario healthy
python -m arc_rpc_evidence demo --scenario failed-receipt
python -m arc_rpc_evidence demo --scenario tip-recover
python -m arc_rpc_evidence demo --scenario conflict
```

Demo использует вымышленные hash и ответы. `request_count` в demo считает
симулированные попытки; `http_request_count` равен нулю. Готовый
[пример с null receipt](evidence/demo-null/report.md) можно читать без запуска.

## Небольшая live проверка

```console
python -m arc_rpc_evidence check --preset mainnet --block 0 --budget 12 --output reports/live
python -m arc_rpc_evidence check --block 100 --block 200 --budget 12
python -m arc_rpc_evidence check --tx 0x0000000000000000000000000000000000000000000000000000000000000000 --budget 12
```

Последний пример проверяет нулевой hash; это демонстрация неизвестного результата,
а не реальная транзакция. Для своей проверки вставьте публичный transaction hash.
Можно передать до трёх `--tx` и `--block` суммарно. Номер блока задаётся десятичным
числом или canonical hex, также принимается block hash. Без targets проверяется
доступность genesis header. Произвольного RPC URL в интерфейсе нет.

Официальные параметры Arc: [chain 5042 и RPC](https://docs.arc.io/arc/references/connect-to-arc).
Preset обращается к `https://rpc.mainnet.arc.io`. При неверном или неподтверждённом
chainId дальнейшие запросы прекращаются.

## Что читать в отчёте

| Поле | Как понимать |
| --- | --- |
| `verified` | Поля ответов согласованы для заданного объекта и закреплённого блока. Это не независимое доказательство finality. |
| `observed-null` | RPC вернул null. Причина неизвестна: возможны pending, задержка backend или недоступность истории. Отсутствие и неуспех не доказаны. |
| `insufficient-evidence` | Ошибка, неполные/неправильные поля, предел запросов или отмена помешали проверке. |
| `inconsistent-observation` | Наблюдения расходятся. Возможны временные изменения у tip; обвинять endpoint оснований нет. |
| `execution: failed` | Receipt status 0x0 согласован с transaction и включением в блок. `verified` при этом допустим. |
| `execution: unknown` | Выполнение не удалось подтвердить. Null receipt не превращается в failed. |

Head закрепляется по number/hash. Возраст head считается по локальным часам;
проверьте время компьютера, прежде чем интерпретировать stale/future. Историческая
проверка касается headers выбранных блоков: она не доказывает полный архив state.
`method_support` описывает только вызванные методы, а не всю RPC спецификацию.

В JSON есть время начала/окончания каждого запроса, параметры, результат либо
статус ошибки. Сообщения ошибок provider не сохраняются: они могут содержать
отражённые приватные данные. Markdown компактно объясняет итог. Перед публикацией
своего отчёта проверьте, что выбранные hash и поля ответа можно публиковать.

## Пределы и отмена

Максимум 24 попытки на запуск, включая retry; `--budget 1..24` уменьшает предел.
Запросы последовательные. Socket timeout 5 секунд, `--timeout` может его уменьшить.
Перед новым запросом проверяется deadline 45 секунд, ответ ограничен 256 KiB.
Заблокированный текущий socket, DNS и TLS могут продлить фактическое время запуска.
Нажмите Ctrl+C: CLI сохранит частичный отчёт, если указан `--output`, и вернёт 130.

[Arc описывает](https://docs.arc.io/arc/references/rpc-endpoints) near-tip `-32014`
у load-balanced backend. Разрешён один retry через 250 ms в пределах двух блоков
от наблюдаемого head, и одно повторное сравнение тех же закреплённых number/hash
при tip-конфликте. Старые блоки и HTTP 429 автоматически не ретраятся.
Ограничение большого getLogs (`-32012`) проверяется только offline fixture;
программа getLogs не отправляет.

`--output reports/имя` создаёт `report.json` и `report.md`. Выберите новую папку,
если файлы уже существуют: перезаписи нет. Код 0 означает, что отчёт сформирован,
а не что все targets verified; 2 означает ошибку параметров или экспорта.

## Проверка проекта

```console
python -m pip install -r requirements-dev.txt
python -m unittest -v
python -m ruff check .
python -m mypy
python -m build
python -m pip check
```

[Первая mainnet проверка](evidence/live-2026-10-08/report.md) содержит восемь
read-only попыток с UTC timestamps для null/genesis.
[Положительный follow-up](evidence/live-positive-2026-10-08/report.md) подтвердил
согласованные transaction/receipt/inclusion и status 0x1 существующей публичной
транзакции. На выбор hash из одного недавнего блока и CLI ушло 11 из 12 попыток;
широкой истории не просматривали. В опубликованном JSON оставлены используемые
проверками поля; неиспользуемые адреса, logs и calldata убраны. Synthetic cases
и live observations лежат отдельно. Нет оценки
скорости, uptime, злонамеренности endpoint или рекомендации покупать активы.
