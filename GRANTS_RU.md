# Arc Microgrants: подготовка заявки

Основной кандидат: [Arc Microgrants](https://community.arc.io/public/events/arc-microgrants-f8tijfjhyq).
[Страница подачи DoraHacks](https://dorahacks.io/hackathon/arc-microgrants/detail).
Обе страницы проверены 8 октября 2026; DoraHacks прочитан в браузере, потому что
web parser возвращал 405. Заявка не подавалась, организаторам ничего не отправлено.

Проверка формы в облачном браузере 8 октября, 21:25 UTC, остановилась на Human
Verification. CAPTCHA, вход и сама форма не проходились. Точные названия кнопок,
полей и дополнительные обязательные материалы здесь не подтверждены. Требование
видео и подключения кошелька именно при подаче публично не установлено.

## Условия, подтверждённые страницами

Программа конкурсная: 20 выплат по 500 USDC, общий pool 10,000 USDC. Требуются
работающий live mainnet проект, публичный repository, открываемая ссылка на
deployment, описание Arc-компонента и публичный builder profile. Нет гарантии
допуска или выплаты. Testnet-only, проекты без Arc и уже финансированная Circle/Arc
работа исключены; остаются jurisdiction/sanctions screening и проверка для payout.

Deadline: **14 октября 2026, 23:59 ET**. На эту дату EDT = UTC−4, поэтому это
15 октября, 03:59 UTC и **15 октября, 06:59 Asia/Jerusalem**; DoraHacks показывал
06:59 на локальном интерфейсе. Решения заявлены до 21 октября, правила/даты могут
измениться. Перед подачей перечитайте обе официальные страницы.

Одна заявка на проект. Правило разрешает **командам несколько разных проектов**.
Возможность нескольких выплат одному solo-разработчику прямо не подтверждена.
Смена названия одного и того же проекта не делает его отдельной разработкой.

## Главный открытый вопрос

Arc RPC Evidence работает с mainnet только через чтение. Правила требуют
deployment на mainnet, но прямо не подтверждают eligibility такого локального
диагностического CLI без контракта. Live RPC smoke и публичный код показывают,
что инструмент работает; они не заменяют одобрение read-only категории и live
deployment URL. **Готовность к допуску не подтверждена.** Не создавайте лишние
on-chain транзакции ради формального вида заявки.

## Честное описание для формы

> Arc RPC Evidence is a read-only developer CLI for explaining a small set of
> Arc mainnet RPC observations. It checks chain identity, pins head and historical
> block headers by number/hash, and compares transaction/receipt fields and block
> inclusion. Null and errors remain unknown rather than being labelled as failed
> transactions. Every request attempt is counted under a 24-request cap. The
> project includes offline replay scenarios, JSON/Markdown evidence, tests and CI.
> It uses the official anonymous Arc mainnet RPC and documents Arc's near-tip
> backend error. No contract is deployed and no transactions are signed or sent.
> Read-only infrastructure eligibility needs confirmation under the program rules.

Repository: https://github.com/kuilef/arc-rpc-evidence

Demo: `python -m arc_rpc_evidence demo --scenario null-receipt`.
Live: `python -m arc_rpc_evidence check --preset mainnet --block 0 --budget 12`.
Evidence: [mainnet observations](evidence/live-2026-10-08/report.md),
[positive receipt check](evidence/live-positive-2026-10-08/report.md),
[synthetic replay](evidence/demo-null/report.md), tests and Actions in repository.
Данные demo вымышлены. Первый live smoke проверил headers и null lookup;
отдельный follow-up согласовал существующую transaction/receipt/inclusion и
status 0x1. На выбор hash и CLI потрачено 11/12 read-only попыток на одном RPC.
Полный архив, независимое доказательство finality и надёжность RPC не заявлены.

## Только пользователь выполняет эти шаги

1. Проверить актуальные правила и самостоятельно уточнить, принимается ли read-only
   инфраструктура. Контакт/вопрос организаторам не отправлялся.
2. Если нужен публичный working demo URL, выбрать hosting, доступ и бюджет.
   Сейчас опубликован код, публичного сервиса нет. Возможный следующий scope —
   статическая локальная demo-view с прямым официальным RPC или воспроизводимая
   запись запуска; организатор должен подтвердить, что такой формат подходит.
   Публичный RPC proxy и произвольные URL не нужны.
3. Открыть Register со страницы Arc, пройти Human Verification и вход лично.
   Найти подачу проекта; создать или выбрать BUIDL, **если интерфейс это предлагает**.
   Заполнить реально показанные поля, проверить профиль и права на работу,
   прочитать и принять условия лично. Отправить заявку и сохранить подтверждение
   её привязки к Arc Microgrants. Созданная страница BUIDL сама по себе не равна
   заявке. Возможность редактирования после подачи не подтверждена.
4. При conditional selection лично пройти identity/KYC/санкционные проверки,
   если они запрошены. Публично identity публиковать не требуется по правилам,
   но exact verification flow заранее здесь не подтверждён.
5. Указать свой payout wallet для USDC на Arc, проверить сеть и владение адресом.
   Wallet не создавался и не подключался. Любые on-chain payment, bridge,
   deployment, gas cost или signatures требуют отдельного решения пользователя.

Публичный GitHub не равен live mainnet deployment. Не отмечайте неподтверждённое
как выполненное и не рассчитывайте грант как гарантированный доход.
