When to read this: Use when writing application code on top of LibXR (v2.0.1) and choosing among its core facilities: Topic, Event, RamFS, Terminal, Database, Logger, Thread, Timer, read/write calls, assertions, and PowerManager.

# LibXR core facilities

LibXR is an embedded C++20 framework that runs the same application code on bare-metal, on an RTOS such as FreeRTOS or ThreadX, and on Linux. The system layer maps threads, mutexes, semaphores, and software timers onto the host platform, and peripheral drivers expose one set of abstract classes (`LibXR::UART`, `LibXR::SPI`, `LibXR::CAN`, ...). Applications link the library as source: add the repository as a CMake subdirectory, select the platform, and link the `xr` target. `LibXR::PlatformInit()` initializes the system layer before threads, timers, and peripherals are used.

```cmake
set(LIBXR_SYSTEM FreeRTOS)
set(LIBXR_DRIVER st)
add_subdirectory(libxr)
target_link_libraries(${CMAKE_PROJECT_NAME} xr)
```

## A running example

One board hosts a small control program:

- An IMU task samples the sensor every millisecond and publishes an `Attitude` struct on a Topic.
- The control thread picks up the newest attitude each cycle and drives the motors.
- The LED thread learns about faults through an Event.
- A `status` command mounted in RamFS prints counters when a developer types it into the terminal.
- The logger records fault entries through `XR_LOG_WARN`.

| Concept | In this scenario |
| --- | --- |
| Topic | the channel the IMU task publishes `Attitude` on |
| Event | the fault notification the LED thread reacts to |
| RamFS and Terminal | the in-memory filesystem that holds the `status` command behind `ls` |
| Database | where calibration offsets survive a reboot |
| Logger | the `XR_LOG_*` macros writing the fault entries |
| Thread and Timer | the IMU task and the periodic housekeeping task |

## Topic: publish and subscribe

A Topic carries typed messages from publishers to subscribers at runtime. Create it once with a name and a payload type, then publish copies of the payload:

```cpp
struct Attitude { float roll, pitch, yaw; };

auto topic = LibXR::Topic::CreateTopic<Attitude>("imu/attitude");
// in the IMU task, once per sample:
Attitude att = imu.Read();
topic.Publish(att);
```

Other code reaches the same topic by name: `Topic::Find("imu/attitude")` returns the existing topic, `Topic::FindOrCreate<Attitude>("imu/attitude")` creates it on first use, and `Topic::WaitTopic("imu/attitude", timeout)` blocks a thread until the topic appears. Publishing from an interrupt or a callback goes through `PublishFromCallback(att, in_isr)`.

Subscribers come in four kinds, enumerated by `Topic::SuberType`: `SYNC` waits synchronously for the next publication, `ASYNC` keeps a local buffer, `QUEUE` forwards publications into a queue, and `CALLBACK` runs a callback per publication. `topic.RegisterCallback(cb)` attaches a callback in the `CALLBACK` style. A topic created with `multi_publisher = false` (the default) has one publishing context; with `multi_publisher = true` several tasks share it and the topic serializes publishers.

The most recent value stays with the application: a consumer that polls for the newest attitude pairs the topic with a latest-value mailbox (see [containers.md](containers.md)), while the topic delivers each publication as it happens.

Reference:

- [Message: Topic](https://xrobot.work/docs/basic_coding/middleware/message/message-topic) — creation, publish semantics, the four subscriber kinds.
- [Topic design](https://xrobot.work/docs/adv_coding/middleware/adv-coding-middleware-topic-design) — why the subscriber kinds exist and how dispatch works.
- [Message system](https://xrobot.work/docs/basic_coding/middleware/message) — packet server and Linux shared topics.

## Event: notification between contexts

An `Event` maps 32-bit event numbers to callbacks. A context registers interest, another context activates the event:

```cpp
enum : uint32_t { EV_FAULT = 0x1, EV_CALIBRATED = 0x2 };

LibXR::Event events;
int fault_count = 0;
auto on_fault = LibXR::Event::Callback::Create(
    [](bool in_isr, int* count, uint32_t event) { ++*count; }, &fault_count);
events.Register(EV_FAULT, on_fault);
```

In thread context, `events.Active(EV_FAULT)` runs the registered callbacks immediately in the calling context. From an interrupt or a callback, use the callback-safe form with the list handle captured beforehand:

```cpp
events.ActiveFromCallback(events.GetList(EV_FAULT), EV_FAULT, /*in_isr=*/true);
```

The callback receives the `in_isr` flag, so one callback body can serve both contexts. `events.Bind(source, source_event, target_event)` forwards one Event instance's event to another, which lets a driver surface its internal events under application event numbers. Registered callbacks stay registered for the lifetime of the `Event` object. A thread that waits rather than callbacks registers a callback that posts a `Semaphore` and waits on it.

The waiting form end to end — an interrupt activates the event, the callback posts the semaphore, a thread waits on the semaphore and processes the data:

```cpp
LibXR::Event events;
LibXR::Semaphore rx_ready;
enum : uint32_t { EV_UART_RX = 0x4 };

// Initialization, thread context: register the posting callback, then capture the list.
auto on_rx = LibXR::Event::Callback::Create(
    [](bool in_isr, LibXR::Semaphore* sem, uint32_t) { sem->PostFromCallback(in_isr); },
    &rx_ready);
events.Register(EV_UART_RX, on_rx);
auto rx_list = events.GetList(EV_UART_RX);

// Interrupt handler: hand off and return.
void uart_irq_handler()
{
  events.ActiveFromCallback(rx_list, EV_UART_RX, /*in_isr=*/true);
}

// Worker thread: wait, then process.
LibXR::Thread worker;
worker.Create<LibXR::Semaphore*>(
    &rx_ready,
    [](LibXR::Semaphore* sem) {
      while (true)
      {
        if (sem->Wait(1000) == LibXR::ErrorCode::OK)
        {
          /* read the bytes the interrupt made available */
        }
      }
    },
    "rx", 512, LibXR::Thread::Priority::HIGH);
```

`GetList` creates the list when the event carries none and runs outside the interrupt, which is why the handle is captured during initialization and only used afterwards. `PostFromCallback(in_isr)` is the interrupt-side post; `Wait(timeout)` answers `ErrorCode::OK` for a post and `ErrorCode::TIMEOUT` when the timeout expires, so the loop keeps a re-arm point instead of stopping forever on a post that never comes. A single peripheral transfer needs no event of its own — `Operation(Semaphore&, timeout)` waits on the same semaphore through the driver's `BLOCK` completion (see the next section).

Reference: [Middleware: Event](https://xrobot.work/docs/basic_coding/middleware/event).

## RamFS and terminal commands

RamFS is an in-memory filesystem. `LibXR::RamFS ramfs;` constructs the root directory plus a `bin` directory (the default root name is `"ramfs"`). Nodes are files, directories, or custom nodes (`FsNodeType` of `FILE`, `DIR`, `CUSTOM`); files carry a `FileType` of `READ_ONLY`, `READ_WRITE`, or `EXEC`. `ramfs.Add(node)` mounts a node, and `Dir::FindDir`, `Dir::FindFile`, and `Dir::Foreach` navigate the tree.

Terminal commands are `EXEC` files. `RamFS::CreateCommand` wraps a function with the signature `int (*)(ArgType arg, int argc, char** argv)` into a command file, and mounting it makes it executable by name:

```cpp
static int StatusCommand(Status* self, int argc, char** argv) { /* ... */ return 0; }

auto* status_cmd = new LibXR::RamFS::File(
    LibXR::RamFS::CreateCommand("status", StatusCommand, &status));
ramfs.Add(*status_cmd);
```

`LibXR::Terminal` (template parameters `READ_BUFF_SIZE = 32`, `MAX_LINE_SIZE = READ_BUFF_SIZE`, `MAX_ARG_NUMBER = 5`, `MAX_HISTORY_NUMBER = 5`) reads a line, resolves the first argument, and executes. At the baseline version the built-in commands are `cd` and `ls`; every other first argument is treated as the path of an executable RamFS file. `ls` marks entries with `d ` (directory), `x ` (executable), `f ` (file), and `? ` (custom node). Tab completion covers the first argument at the end of a line, and the arrow keys edit history. Printing a file's contents goes through an application-registered command. On generated BSPs a UART or USB CDC port typically feeds the terminal.

Reference:

- [Middleware: RamFS](https://xrobot.work/docs/basic_coding/middleware/ramfs)
- [Middleware: Terminal](https://xrobot.work/docs/basic_coding/middleware/terminal)

## Database: key-value storage across reboots

`Database` stores named values in flash with typed keys derived from `Database::KeyBase`, so calibration constants, configuration, and cumulative counters survive a power cycle. The on-flash layout carries a format version (`LIBXR_DATABASE_VERSION = 3`) checked when stored data is loaded, and raw variants (`DatabaseRaw`, `DatabaseRawSequential`) cover untyped byte data.

Topic and Database answer different questions. A Topic moves runtime data between contexts and each publication is consumed as it happens; the Database keeps small named values until they are overwritten. In the running example, attitude samples flow over a Topic every millisecond, while the IMU's calibration offsets load from the Database at boot and are written back after calibration.

Reference: [Middleware: Database](https://xrobot.work/docs/basic_coding/middleware/database).

## Logger

`XR_LOG_ERROR`, `XR_LOG_WARN`, `XR_LOG_PASS`, `XR_LOG_INFO`, and `XR_LOG_DEBUG` format at compile time and publish the entry to an internal log Topic, from which a terminal or other middleware can echo it. Levels are `ERROR = 0`, `WARN = 1`, `PASS = 2`, `INFO = 3`, `DEBUG = 4`. `LIBXR_LOG_LEVEL` (default 4) selects which levels compile in; `LIBXR_LOG_OUTPUT_LEVEL` (default 4) controls what the output side emits. The formatted message lands in a fixed buffer of `XR_LOG_MESSAGE_MAX_LEN` bytes — 64 by default, 256 on the Linux, Webots, and WebAssembly system layers.

```cpp
XR_LOG_WARN("imu fell back to gyro-only mode");
```

Reference: [Middleware: Logger](https://xrobot.work/docs/basic_coding/middleware/logger).

## Threads and timers

`LibXR::Thread` is a handle; `Create` starts it once and runs `function(arg)`:

```cpp
LibXR::Thread thread;
thread.Create<LibXR::Semaphore*>(
    &sem,
    [](LibXR::Semaphore* sem) { sem->Post(); },
    "worker", 512, LibXR::Thread::Priority::REALTIME);
```

`Thread::Sleep(ms)` pauses the calling thread, and `Thread::SleepUntil(wakeup, period)` implements periodic loops from a persistent `MillisecondTimestamp`. Priorities `IDLE`, `LOW`, `MEDIUM`, `HIGH`, and `REALTIME` map onto the host scheduler; on the bare-metal `none` system layer they collapse to a single level. `Mutex`, `Semaphore`, and `ASync` round out the system layer.

`LibXR::Timer` runs periodic callbacks at millisecond resolution:

```cpp
static int ticks = 0;
auto task = LibXR::Timer::CreateTask<int*>(
    [](int* count) { ++*count; }, &ticks, 10);
LibXR::Timer::Add(task);
LibXR::Timer::Start(task);
```

`CreateTask(fun, arg, cycle_ms)` builds the task, `Add` registers it with the timer manager, `Start`/`Stop` toggle it, and `SetCycle` changes the period. On threaded systems the tasks execute in a dedicated timer management thread; on the bare-metal and WebAssembly system layers the timer list refreshes while the system idles.

Reference:

- [Operating system layer](https://xrobot.work/docs/basic_coding/system) — platform initialization and porting.
- [Thread](https://xrobot.work/docs/basic_coding/system/thread) and [Timer](https://xrobot.work/docs/basic_coding/system/timer).

## Interrupt and thread boundaries

The working set for application code:

- An interrupt hands data off and returns. Non-blocking exchanges run there: `LatestSnapshot::Store`, `SlotPool` `Put`/`Get`, `Event::ActiveFromCallback`, `Topic::PublishFromCallback`, and driver `Read`/`Write` calls with `CALLBACK` or `NONE` completion.
- Waiting happens in threads. `BLOCK` completion on ReadPort/WritePort runs in thread context only; an interrupt keeps to non-blocking calls and skips loop retries and mutexes.
- An `MPMCQueue` shared with an interrupt reports transient `FULL`/`EMPTY` while a preempted operation is mid-handover (details in [containers.md](containers.md)).
- Callbacks reached through the `*FromCallback` entry points receive the `in_isr` flag; the same body serves both contexts.
- Critical sections stay short and local: registers and atomics inside, callbacks and queue or transfer operations outside.
- `ObjectPool` serves interrupts on platforms with 32-bit CAS; pool construction and destruction run outside interrupt context.

Reference:

- [ISR, callback, and thread boundaries](https://xrobot.work/docs/adv_coding/core/adv-coding-core-isr-thread-boundary)
- [Design principles](https://xrobot.work/docs/concept) — the six principles behind these rules.

## Blocking, timeout, and completion for read/write calls

Driver I/O such as `UART`, `SPI`, and `I2C` goes through ReadPort/WritePort, and every call takes an Operation that states how completion is reported:

| Operation | Construction | Behavior |
| --- | --- | --- |
| `CALLBACK` | `Operation(Callback&)` | completion runs the callback once, in the context that finishes the operation (the current call, a driver task, or an interrupt) |
| `BLOCK` | `Operation(Semaphore&, timeout)` | the call waits and returns the final result or `ErrorCode::TIMEOUT`; thread context only |
| `POLLING` | `Operation(std::atomic<OperationPollingStatus>&)` | the caller reads the atomic status (`READY`, `RUNNING`, `DONE`, `ERROR`) |
| `NONE` | default | the request runs without a completion notification |

Return values describe acceptance. For a non-BLOCK call, `OK` means the request was accepted — the data is already copied into the internal queue — with completion still to come. `FULL` rejects the request without partial acceptance, `BUSY` reports a conflicting operation on the same port, a read larger than the receive queue reports `SIZE_ERR`, and an unbound port reports `NOT_SUPPORT`. A zero-length read waits for the receive queue to hold data and consumes nothing — an availability probe. When a timeout and a completion race on the same request, the timed-out call may return after the specified timeout while the late completion is drained without touching the caller's semaphore.

Reference:

- [Operation model](https://xrobot.work/docs/basic_coding/core/core-op) and [IO abstraction](https://xrobot.work/docs/basic_coding/core/core-rw)
- [IO completion semantics](https://xrobot.work/docs/adv_coding/core/adv-coding-core-rw-semantics) — port state machines in depth.
- [BLOCK timeout and handover](https://xrobot.work/docs/adv_coding/driver/adv-coding-drv-block-timeout-semantics)

## Assertions and fatal errors

Three macros live in `src/core/libxr_def.hpp`:

- `ASSERT(arg)` — caller-side checks such as arguments and fixed configuration. Active under `LIBXR_DEBUG_BUILD`; when the build disables it, the expression is still evaluated, so side effects belong outside the macro.
- `DEV_ASSERT(arg)` — library-internal development checks. Disabled and unevaluated unless the build defines `LIBXR_DEV_ASSERT_BUILD`.
- `REQUIRE(arg)` — unrecoverable runtime failures such as resource exhaustion or a broken initialization contract; active in every configuration. Recoverable conditions come back as an `ErrorCode` instead.

A failed check enters `libxr_fatal_error`. In thread context it prints `Fatal error at {file}:{line}` when STDIO is bound, runs the callback registered with `LibXR::Assert::RegisterFatalErrorCallback`, and then sleeps in a loop; in interrupt context it writes through a null pointer so the hardware fault handler stops the core.

CMake switches: `LIBXR_DEBUG_BUILD` follows the build type when unset (Debug builds get it, others lose it) and a plain `-DLIBXR_DEBUG_BUILD=OFF` (or `ON`) fixes it for that build tree. `LIBXR_DEV_ASSERT_BUILD` is a CMake option, off by default, used when developing the library itself.

Reference: [Assertions](https://xrobot.work/docs/basic_coding/core/core-assert), [Common definitions](https://xrobot.work/docs/basic_coding/core/core-def), [CMake configuration](https://xrobot.work/docs/basic_coding/basic-cmake).

## PowerManager and the power command

`PowerManager` is the abstract base for platform power control with `Reset()`, `Shutdown()`, and `JumpToBootloader()`; platforms without a bootloader entry fall back to `Reset()` for the jump. `RegisterCommand(ramfs)` mounts a `power` command in the RamFS root:

```text
power reset        -> Reset()
power shutdown     -> Shutdown()
power bootloader   -> JumpToBootloader()
```

`power` with a missing or unknown argument prints `usage: power reset|shutdown|bootloader` and returns -1. `CheckBootloaderPin(pin, level)` reads a GPIO once and calls `JumpToBootloader()` when the pin reads `level`; call it early at startup, and drive or pull the pin deliberately — a floating pin can match by accident.

Reference: [Driver: Power](https://xrobot.work/docs/basic_coding/driver/power), [Middleware: Terminal](https://xrobot.work/docs/basic_coding/middleware/terminal).

## Where to read more

- [Basic coding (LibXR)](https://xrobot.work/docs/basic_coding) — the entry page for every component above.
- [API reference](https://xrobot.work/libxr/) — Doxygen-style class documentation.
- [containers.md](containers.md) — choosing between LatestSnapshot, the queue family, SlotPool, and ObjectPool.
