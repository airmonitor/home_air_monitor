import utime
import sys
import uio

CRITICAL = 50
ERROR    = 40
WARNING  = 30
INFO     = 20
DEBUG    = 10
NOTSET   = 0

_level_dict = {
    CRITICAL: "CRITICAL",
    ERROR: "ERROR",
    WARNING: "WARNING",
    INFO: "INFO",
    DEBUG: "DEBUG",
}

def add_level_name(level, name):
    _level_dict[level] = name

class Logger:

    level = NOTSET

    def __init__(self, name):
        self.name = name
        self.handlers = None
        self.parent = None

    @staticmethod
    def _level_str(level):
        l = _level_dict.get(level)
        return l if l is not None else "LVL%s" % level

    def set_level(self, level):
        self.level = level

    def is_enabled_for(self, level):
        return level >= self.level

    def log(self, level, msg, *args):
        dest = self
        while dest.level == NOTSET and dest.parent:
            dest = dest.parent
        if level >= dest.level:
            record = LogRecord(
                self.name, level, None, None, msg, args, None, None, None
            )

            if dest.handlers:
                for handler in dest.handlers:
                    handler.emit(record)

    def debug(self, msg, *args):
        self.log(DEBUG, msg, *args)

    def info(self, msg, *args):
        self.log(INFO, msg, *args)

    def warning(self, msg, *args):
        self.log(WARNING, msg, *args)

    warn = warning

    def error(self, msg, *args):
        self.log(ERROR, msg, *args)

    def critical(self, msg, *args):
        self.log(CRITICAL, msg, *args)

    def exc(self, e, msg, *args):
        buf = uio.StringIO()
        sys.print_exception(e, buf)
        self.log(ERROR, msg + "\n" + buf.getvalue(), *args)

    def exception(self, msg, *args):
        self.exc(sys.exc_info()[1], msg, *args)

    def add_handler(self, handler):
        if self.handlers is None:
            self.handlers = []
        self.handlers.append(handler)


def get_logger(name=None):
    if name is None:
        name = "root"
    if name in _loggers:
        return _loggers[name]
    l = Logger(name)
    # For now, we have shallow hierarchy, where the parent of each logger is root.
    l.parent = root
    _loggers[name] = l
    return l

def info(msg, *args):
    get_logger(None).info(msg, *args)

def debug(msg, *args):
    get_logger(None).debug(msg, *args)

def warning(msg, *args):
    get_logger(None).warning(msg, *args)

warn = warning

def error(msg, *args):
    get_logger(None).error(msg, *args)

def critical(msg, *args):
    get_logger(None).critical(msg, *args)

def exception(msg, *args):
    get_logger(None).exception(msg, *args)

def basic_config(level=INFO, filename=None, stream=None, log_format=None, style="%"):
    root.set_level(level)
    h = FileHandler(filename) if filename else StreamHandler(stream)
    h.set_formatter(Formatter(log_format or "%(levelname)s:%(name)s:%(message)s", style=style))
    root.handlers.clear()
    root.add_handler(h)


class Handler:
    def __init__(self):
        self.formatter = Formatter()

    def set_formatter(self, fmt):
        self.formatter = fmt


class StreamHandler(Handler):
    def __init__(self, stream=None):
        super().__init__()
        self._stream = stream or sys.stderr
        self.terminator = "\n"

    def emit(self, record):
        self._stream.write(self.formatter.format(record) + self.terminator)

    def flush(self):
        pass


class FileHandler(StreamHandler):
    def __init__(self, filename, mode="a", encoding=None, delay=False):
        super().__init__(None)

        self.encoding = encoding
        self.mode = mode
        self.delay = delay
        self.filename = filename

        if not delay:
            self._stream = open(self.filename, self.mode)

    def emit(self, record):
        if self._stream is None:
            self._stream = open(self.filename, self.mode)

        super().emit(record)

    def close(self):
        if self._stream is not None:
            self._stream.close()


class Formatter:

    converter = utime.localtime

    def __init__(self, fmt=None, date_format=None, style="%"):
        self.fmt = fmt or "%(message)s"
        self.date_format = date_format

        if style not in ("%", "{"):
            raise ValueError("Style must be one of: %, {")

        self.style = style

    def uses_time(self):
        if self.style == "%":
            return "%(asctime)" in self.fmt
        elif self.style == "{":
            return "{asctime" in self.fmt

    def format(self, record):
        # The message attribute of the record is computed using msg % args.
        record.message = record.msg % record.args

        # If the formatting string contains '(asctime)', formatTime() is called to
        # format the event time.
        if self.uses_time():
            record.asctime = self.format_time(record, self.date_format)

        # If there is exception information, it is formatted using formatException()
        # and appended to the message. The formatted exception information is cached
        # in attribute exc_text.
        if record.exc_info is not None:
            record.exc_text += self.format_exception(record.exc_info)
            record.message += "\n" + record.exc_text

        # The record’s attribute dictionary is used as the operand to a string-formatting operation.
        if self.style == "%":
            return self.fmt % record.__dict__
        elif self.style == "{":
            return self.fmt.format(**record.__dict__)
        else:
            raise ValueError(
                "Style {0} is not supported by logging.".format(self.style)
            )

    @staticmethod
    def format_time(record, date_format=None):
        assert date_format is None  # datefmt is not supported
        ct = utime.localtime(record.created)
        return "{0}-{1}-{2} {3}:{4}:{5}".format(*ct)

    def format_exception(self, exc_info):
        raise NotImplementedError()

    def format_stack(self, stack_info):
        raise NotImplementedError()


class LogRecord:
    def __init__(
        self, name, level, pathname, lineno, msg, args, exc_info, func=None, sinfo=None
    ):
        ct = utime.time()
        self.created = ct
        self.msecs = (ct - int(ct)) * 1000
        self.name = name
        self.levelno = level
        self.levelname = _level_dict.get(level)
        self.pathname = pathname
        self.lineno = lineno
        self.msg = msg
        self.args = args
        self.exc_info = exc_info
        self.func = func
        self.sinfo = sinfo


root = Logger("root")
root.set_level(WARNING)
sh = StreamHandler()
sh.formatter = Formatter()
root.add_handler(sh)
_loggers = {"root": root}
