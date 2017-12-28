import sys

if sys.platform == 'win32':
    from ctypes import byref, c_int64, windll
    _fcounter = c_int64()
    _qpfreq = c_int64()
    windll.Kernel32.QueryPerformanceFrequency(byref(_qpfreq))
    _qpfreq = float(_qpfreq.value)
    _winQPC = windll.Kernel32.QueryPerformanceCounter

    def getTime():
        _winQPC(byref(_fcounter))
        return _fcounter.value / _qpfreq
else:
    import timeit
    getTime = timeit.default_timer


class MonoClock(object):

    def __init__(self, start_time=None):
        if start_time is None:
            # this is sub-millisec timer in python
            self._timeAtLastReset = getTime()
        else:
            self._timeAtLastReset = start_time

    def getTime(self):
        """Returns the current time on this clock in secs (sub-ms precision)
        """
        return getTime() - self._timeAtLastReset

    def getLastResetTime(self):
        """
        Returns the current offset being applied to the high resolution
        timebase used by Clock.
        """
        return self._timeAtLastReset

monoClock = MonoClock()