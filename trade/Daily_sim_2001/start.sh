###stop ####

process_pid=`ps -ef|grep runDailyTrading_sim_2001.py|grep -v grep`
echo "process_pid  "$process_pid
if [   -n "$process_pid" ]; then

    kill -9 `ps -ef| grep "runDailyTrading_sim_2001.py" | grep -v "grep"  | awk '{print $2}'`
    echo "stop process ok!!!!"
fi

#### start  ###
echo `pwd`

nohup  python runDailyTrading_sim_2001.py &

echo "start  ok!!!"