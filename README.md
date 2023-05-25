# `birdsong`

A dynamically-loaded custom command manager for phase two of `The Forest` Discord server.

## Installation

1. Install dependencies using `poetry`.
```sh
$ poetry install
```

***

## Using `birdsong`

1. Create a configuration file at `config/config.yaml`. You can see `config/config.example.yaml` for an example. 
   **NEVER commit your `config.yaml` file to version control or you will leak your client token!**

2. Run the bot.
```zsh
$ poetry run birdsong
```

***

## Using `supervisor`

1. Create a configuration file at `supervisord.conf`. It should look something like this:
```ini
[supervisorctl]

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisord]
logfile=/home/rsarvaria/birdsong/logs/supervisord.log

[inet_http_server]         
port=127.0.0.1:9001

[program:birdsong]
command=poetry run birdsong
redirect_stderr=true
stdout_logfile=/home/rsarvaria/birdsong/logs/process.log
```

2. Start `supervisord`.
```sh
$ poetry run supervisord
```

3. Ensure that the process we created started successfully.
```sh
$ poetry run supervisorctl

birdsong                         RUNNING   pid 548159, uptime 3 days, 17:59:32
supervisor> 
```

***

## Command library

`birdsong` commands consist of two parts: a command specfile and a command script.

***

## Command specifications

Specfiles are written in YAML and dictate how the bot should respond to a particular
trigger in a particular context. Each time a user sends a message, each command is 
tested against its specfile to see if the command should run in the current context.
Each specfile that matches is then run in sequence for that message. 

Here is an example of a simple specfile that defines a command:

```yaml
cmdtype: "command"
trigger: "slap"

require:
    channels:
        - "bots"
    roles:
        - "Slapper"

actions: "./slap.py"
```

Specfiles contain four blocks:
- `cmdtype`: The type of the custom command. Can be one of the following:
    - `command`: matches the classic command form `{prefix}{cmd} [args]`.
    - `contains`: triggers if the trigger is anywhere in the message (case insensitive).
    - `exact`: triggers if the message content is exactly the same as the trigger.
    - `regex`: triggers depending on the given regular expression.
- `trigger`: The string that the bot matches according to the rules set by `cmdtype`; for instance, the name of the command.
- `require`: A block of lists of conditions that the trigger message has to satisfy. Options include the following:
    - `channels`: A list of channels where the command can run.
    - `categories`: A list of categories where the command can run.
    - `roles`: The user must have at least one of these roles to use the command.
- `actions`: A path to the Python file that implements the command. More on this below.

***

## Command scripting

Scripts are written in Python and interact directly with the `birdsong` client to interact 
with Discord or the database. 

Each script must have the following basic structure:

```py
import discord


async def action(birdsong: any, context: discord.Message, cmd: str, args: list[str]) -> bool:
    """
    Implements an action.
    """
    await do_things()
```

The return value of `action` should be `true` if you wish to delete the `context` message, and false otherwise.
- if any `action` triggered by a message returns `true`, the message is deleted at _the end_ of execution
- **DO NOT delete the message directly** or other trigger commands will lose access to the command context!

The `birdsong` parameter provides access to the following:
- `birdsong.assetmanager`: An asset manager that handles loading and storing files from your `assets` and `store` paths.
- `birdsong.builtins`: A collection of helper functions that are super helpful for simplifying script files.
- `birdsong.ccmanager`: Underlying access to `birdsong`'s custom command framework. _(Use with caution.)_
- `birdsong.dbmanager`: A wrapper around `birdsong`'s connection to `mongodb`.
- `birdsong.modules`: A collection of modules loaded from the `modules` path. Modules are globally available in scripts.

***

## Recommended project structure

Here is an example of a single-project layout using `birdsong`.

```
birdsong
├── birdsong
├── config
├── .gitignore
├── poetry.lock
├── pyproject.toml
├── README.md
└── supervisord.conf
my-command-project
├── docs
│  └── README.md
└── impl
   ├── assets
   ├── commands
   │  ├── slap.py
   │  └── slap.yaml
   ├── commands
   │  └── mymodule.py
   └── store
```

If you are interested in a multi-project layout instead, you might want to do something like this:
```
birdsong
├── birdsong
├── config
├── .gitignore
├── poetry.lock
├── pyproject.toml
├── README.md
└── supervisord.conf
my-projects
├── assets
│  ├── project-a
│  │  └── image_a.png
│  └── project-b 
│     └── image_b.png
├── commands
│  ├── project-a
│  │  ├── command_a.py
│  │  └── command_a.yaml
│  └── project-b
│     ├── command_b.py
│     └── command_b.yaml
├── docs
│  ├── project-a
│  │  └── README.md
│  └── project-b 
│     └── README.md
├── modules
│  ├── project-a.py
│  └── project-b.py 
└── store
   ├── project-a
   │  └── generated_a.png
   └── project-b 
      └── generated_b.png
```