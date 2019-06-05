case ONFRONTCONNECTED:
{
	this->processFrontConnected(task);
	break;
}

case ONFRONTDISCONNECTED:
{
	this->processFrontDisconnected(task);
	break;
}

case ONHEARTBEATWARNING:
{
	this->processHeartBeatWarning(task);
	break;
}

case ONRSPUSERLOGIN:
{
	this->processRspUserLogin(task);
	break;
}

case ONRSPUSERLOGOUT:
{
	this->processRspUserLogout(task);
	break;
}

case ONRSPERROR:
{
	this->processRspError(task);
	break;
}

case ONRSPSUBMARKETDATA:
{
	this->processRspSubMarketData(task);
	break;
}

case ONRSPUNSUBMARKETDATA:
{
	this->processRspUnSubMarketData(task);
	break;
}

case ONRSPSUBFORQUOTERSP:
{
	this->processRspSubForQuoteRsp(task);
	break;
}

case ONRSPUNSUBFORQUOTERSP:
{
	this->processRspUnSubForQuoteRsp(task);
	break;
}

case ONRTNDEPTHMARKETDATA:
{
	this->processRtnDepthMarketData(task);
	break;
}

case ONRTNFORQUOTERSP:
{
	this->processRtnForQuoteRsp(task);
	break;
}

