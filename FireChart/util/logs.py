import logging

import coloredlogs


class Logs(logging.Logger):
    def __init__(self , name: str):
        """

        :param name: 로거명
        """
        super().__init__(name)
        stream = self.makeStreamHandler()

        # self.log: logging.Logger = logging.getLogger(name)
        super().addHandler(hdlr=stream)
        super().setLevel(logging.INFO)
        coloredlogs.install(level='INFO' ,
                            fmt='%(asctime)s %(name)s[%(process)d][%(filename)s:%(lineno)s] %(levelname)s %(message)s' ,
                            logger=self)

    def makeStreamHandler(self , level: int = logging.DEBUG):
        """

        :param level: 로거 레벨
        :return:
        """
        stream = logging.StreamHandler()
        stream.flush()
        stream.setLevel(level=level)
        stream.setFormatter(fmt=logging.Formatter("%(asctime)s [%(levelname)s] %(process)d %(thread)s %(module)s: %(message)s" , "%Y-%m-%d %H:%M:%S"))
        return stream
