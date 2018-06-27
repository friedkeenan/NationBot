# NationBot

This script runs a bot that runs a towny nation as if it were a company. You can buy and sell shares among fellow nation members, and your voting power is determined by how many shares you have. It was created to be used specifically with [AvatarMC](https://www.avatarmc.com), but it should work for any towny server with some slight modifications.

# How to use

This script should run fine on any OS where you can execute a file with ./file (it's trivial to make it work on Windows (look for the os.execv() statements), but I run Linux so I don't care enough). It also requires the [pyCraft library](https://github.com/ammaraskar/pycraft). Most everything will work except for the **restart** command and the server restart logic. It should create the folders Storage and ChatLogs on the first run.

To run the script, simply fill in the appropriate information into config.py and run nation.py. If it fails to connect, it will retry every five seconds until it succeeds. It will run until the admin gives it the **stop** command or you tell it to stop through some other means. Some errors might happen if there are 0 shares in total, so just modify Storage/members.json to put some shares into circulation.

It receives commands through private messages, and commands can be separated with "//".

# Commands

**Admin only commands**
- say [message]
  - Will send the message to chat
- stop
  - Will stop the bot
- restart
  - Will restart the bot, adding any changes you made to the script
- reconnect
  - Will reset the bot's connection
- exec [code]
  - Executes the code. Statements are separated by semi-colons.

**Member only commands**
- balance
  - Replies with the amount of shares you have out of the total shares, and gives a percentage of how many shares you own
- vote
  - make [name] [proposition]
    - Will create a vote with the name 'name' and the proposition 'proposition'
  - vote [name] [yes/no]
    - Adds your shares to the vote with the name 'name'
  - list
    - Lists all votes that are able to be voted on
  - info [name]
    - Tells sender the proposition of the vote, how many shares are for or against it, and how much time is left
- deal
  - sell [buyer] [shares] [money]
    - Creates a deal between sender and buyer that says seller will give buyer the shares if buyer gives seller the money
  - accept [seller]
    - Accepts the deal the sender had with the seller
  - deny [seller]
    - Denies the deal the sender had with the seller
    
**Commands for everyone**
- kinkshame
  - Will kinkshame the sender
- ping
  - Replies with "pong"
- joinTown
  - Will send a town invite to the sender (requires the bot to have proper permissions)
- addTown [town]
  - Will register town as part of nation only if the town is actually in the nation
- addMember [name]
  - Will register 'name' as a nation member only if their town has been registered. All members start with 0 shares.
