
from interface import Parser

###############################################################################
#
# Simple Parser implementation
#
class SimpleParser(Parser):
    ''' simple parser, don't parse ESC/CSI/string seqneces '''

    class _MockContext:

        output = []

        def __iter__(self):
            for i in [1, 2, 3, 4, 5]:
                yield i

        def dispatch_char(self, c):
            self.output.append(c)

    def parse(self, context):
        """
        >>> parser = SimpleParser()
        >>> context = SimpleParser._MockContext()
        >>> parser.parse(context)
        >>> context.output
        [1, 2, 3, 4, 5]
        """
        for c in context:
            context.dispatch_char(c)


###############################################################################
#
# Default Parser implementation
#
_STATE_GROUND = 0
_STATE_ESC = 1
_STATE_ESC_INTERMEDIATE = 2
_STATE_CSI_PARAMETER = 3
_STATE_CSI_INTERMEDIATE = 4
_STATE_SS2 = 6
_STATE_SS3 = 7
_STATE_OSC = 8
_STATE_OSC_ESC = 9
_STATE_STR = 10
_STATE_STR_ESC = 11


class _MockHandler:

    def handle_csi(self, context, parameter, intermediate, final):
        print (parameter, intermediate, final)

    def handle_esc(self, context, intermediate, final):
        print (intermediate, final)

    def handle_control_string(self, context, prefix, value):
        print (prefix, value)

    def handle_char(self, context, c):
        print (c)


class DefaultParser(Parser):
    ''' parse ESC/CSI/string seqneces '''

    def __init__(self):
        self.__state = _STATE_GROUND
        self.__pbytes = []
        self.__ibytes = []

    def init(self, context):
        self.__context = context

    def state_is_esc(self):
        return self.__state == _STATE_ESC

    def reset(self):
        self.__state = _STATE_GROUND

    def parse(self, data):

        context = self.__context
        context.assign(data)
        pbytes = self.__pbytes
        ibytes = self.__ibytes
        state = self.__state
        for c in context:

            if state == _STATE_GROUND:
                if c == 0x1b:  # ESC
                    ibytes = []
                    state = _STATE_ESC

                else:  # control character
                    context.dispatch_char(c)

            elif state == _STATE_ESC:
                #
                # - ISO-6429 independent escape sequense
                #
                #     ESC F
                #
                # - ISO-2022 designation sequence
                #
                #     ESC I ... I F
                #
                if c == 0x5b:  # [
                    pbytes = []
                    state = _STATE_CSI_PARAMETER
                elif c == 0x5d:  # ]
                    pbytes = [c]
                    state = _STATE_OSC
                elif c == 0x4e:  # N
                    state = _STATE_SS2
                elif c == 0x4f:  # O
                    state = _STATE_SS3
                elif c == 0x50 or c == 0x58 or c == 0x5e or c == 0x5f:
                    # P(DCS) or X(SOS) or ^(PM) or _(APC)
                    pbytes = [c]
                    state = _STATE_STR
                elif c < 0x20:  # control character
                    if c == 0x1b:  # ESC
                        seq = [0x1b]
                        context.dispatch_invalid(seq)
                        ibytes = []
                        state = _STATE_ESC
                    elif c == 0x18 or c == 0x1a:
                        seq = [0x1b]
                        context.dispatch_invalid(seq)
                        context.dispatch_char(c)
                        state = _STATE_GROUND
                    else:
                        context.dispatch_char(c)
                elif c <= 0x2f:  # SP to /
                    ibytes.append(c)
                    state = _STATE_ESC_INTERMEDIATE
                elif c <= 0x7e:  # ~
                    context.dispatch_esc(ibytes, c)
                    state = _STATE_GROUND
                elif c == 0x7f:  # control character
                    context.dispatch_char(c)
                else:
                    seq = [0x1b, c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND

            elif state == _STATE_CSI_PARAMETER:
                # parse control sequence
                #
                # CSI P ... P I ... I F
                #     ^
                if c > 0x7e:
                    if c == 0x7f:  # control character
                        context.dispatch_char(c)
                    else:
                        seq = [0x1b, 0x5b] + pbytes
                        context.dispatch_invalid(seq)
                        state = _STATE_GROUND
                elif c > 0x3f:  # Final byte, @ to ~
                    context.dispatch_csi(pbytes, ibytes, c)
                    state = _STATE_GROUND
                elif c > 0x2f:  # parameter, 0 to ?
                    pbytes.append(c)
                elif c > 0x1f:  # intermediate, SP to /
                    ibytes.append(c)
                    state = _STATE_CSI_INTERMEDIATE

                # control chars
                elif c == 0x1b:  # ESC
                    seq = [0x1b, 0x5b] + pbytes
                    context.dispatch_invalid(seq)
                    ibytes = []
                    state = _STATE_ESC

                elif c == 0x18 or c == 0x1a:  # CAN, SUB
                    seq = [0x1b, 0x5b] + pbytes
                    context.dispatch_invalid(seq)
                    context.dispatch_char(c)
                    state = _STATE_GROUND

                else:
                    context.dispatch_char(c)

            elif state == _STATE_CSI_INTERMEDIATE:
                # parse control sequence
                #
                # CSI P ... P I ... I F
                #             ^
                if c > 0x7e:
                    if c == 0x7f:  # control character
                        context.dispatch_char(c)
                    else:
                        seq = [0x1b, 0x5b] + pbytes + ibytes
                        context.dispatch_invalid(seq)
                        state = _STATE_GROUND
                elif c > 0x3f:  # Final byte, @ to ~
                    context.dispatch_csi(pbytes, ibytes, c)
                    state = _STATE_GROUND
                elif c > 0x2f:
                    seq = [0x1b, 0x5b] + pbytes + ibytes + [c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND
                elif c > 0x1f:  # intermediate, SP to /
                    ibytes.append(c)
                    state = _STATE_CSI_INTERMEDIATE

                # control chars
                elif c == 0x1b:  # ESC
                    seq = [0x1b, 0x5b] + pbytes + ibytes
                    context.dispatch_invalid(seq)
                    ibytes = []
                    state = _STATE_ESC
                elif c == 0x18 or c == 0x1a:
                    seq = [0x1b, 0x5b] + pbytes + ibytes
                    context.dispatch_invalid(seq)
                    context.dispatch_char(c)
                    state = _STATE_GROUND
                else:
                    context.dispatch_char(c)

            elif state == _STATE_ESC_INTERMEDIATE:
                if c > 0x7e:
                    if c == 0x7f:  # control character
                        context.dispatch_char(c)
                    else:
                        seq = [0x1b] + ibytes + [c]
                        context.dispatch_invalid(seq)
                        state = _STATE_GROUND
                elif c > 0x2f:  # 0 to ~, Final byte
                    context.dispatch_esc(ibytes, c)
                    state = _STATE_GROUND
                elif c > 0x1f:  # SP to /
                    ibytes.append(c)
                    state = _STATE_ESC_INTERMEDIATE
                elif c == 0x1b:  # ESC
                    seq = [0x1b] + ibytes
                    context.dispatch_invalid(seq)
                    ibytes = []
                    state = _STATE_ESC
                elif c == 0x18 or c == 0x1a:
                    seq = [0x1b] + ibytes
                    context.dispatch_invalid(seq)
                    context.dispatch_char(c)
                    state = _STATE_GROUND
                else:
                    context.dispatch_char(c)

            elif state == _STATE_OSC:
                # parse control string
                if c == 0x07:
                    context.dispatch_control_string(pbytes[0], ibytes)
                    state = _STATE_GROUND
                elif c < 0x08:
                    seq = [0x1b] + pbytes + ibytes + [c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND
                elif c < 0x0e:
                    ibytes.append(c)
                elif c == 0x1b:
                    state = _STATE_OSC_ESC
                elif c < 0x20:
                    seq = [0x1b] + pbytes + ibytes + [c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND
                else:
                    ibytes.append(c)

            elif state == _STATE_STR:
                # parse control string
                # 00/08 - 00/13, 02/00 - 07/14
                #
                if c < 0x08:
                    seq = [0x1b] + pbytes + ibytes + [c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND
                elif c < 0x0e:
                    ibytes.append(c)
                elif c == 0x1b:
                    state = _STATE_STR_ESC
                elif c < 0x20:
                    seq = [0x1b] + pbytes + ibytes + [c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND
                else:
                    ibytes.append(c)

            elif state == _STATE_OSC_ESC:
                # parse control string
                if c == 0x5c:
                    context.dispatch_control_string(pbytes[0], ibytes)
                    state = _STATE_GROUND
                else:
                    seq = [0x1b] + pbytes + ibytes + [0x1b, c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND

            elif state == _STATE_STR_ESC:
                # parse control string
                # 00/08 - 00/13, 02/00 - 07/14
                #
                if c == 0x5c:
                    context.dispatch_control_string(pbytes[0], ibytes)
                    state = _STATE_GROUND
                else:
                    seq = [0x1b] + pbytes + ibytes + [0x1b, c]
                    context.dispatch_invalid(seq)
                    state = _STATE_GROUND

            elif state == _STATE_SS3:
                if c < 0x20:  # control character
                    if c == 0x1b:  # ESC
                        seq = [0x1b, 0x4f]
                        context.dispatch_invalid(seq)
                        ibytes = []
                        state = _STATE_ESC
                    elif c == 0x18 or c == 0x1a:
                        seq = [0x1b, 0x4f]
                        context.dispatch_invalid(seq)
                        context.dispatch_char(c)
                        state = _STATE_GROUND
                    else:
                        context.dispatch_char(c)
                elif c < 0x7f:
                    context.dispatch_ss3(c)
                    state = _STATE_GROUND
                else:
                    seq = [0x1b, 0x4f]
                    context.dispatch_invalid(seq)
                    context.dispatch_char(c)

            elif state == _STATE_SS2:
                if c < 0x20:  # control character
                    if c == 0x1b:  # ESC
                        seq = [0x1b, 0x4e]
                        context.dispatch_invalid(seq)
                        ibytes = []
                        state = _STATE_ESC
                    elif c == 0x18 or c == 0x1a:
                        seq = [0x1b, 0x4e]
                        context.dispatch_invalid(seq)
                        context.dispatch_char(c)
                        state = _STATE_GROUND
                    else:
                        context.dispatch_char(c)
                elif c < 0x7f:
                    context.dispatch_ss2(c)
                    state = _STATE_GROUND
                else:
                    seq = [0x1b, 0x4f]
                    context.dispatch_invalid(seq)
                    context.dispatch_char(c)

        self.__pbytes = pbytes
        self.__ibytes = ibytes
        self.__state = state


def _test():
    import doctest
    doctest.testmod()

''' main '''
if __name__ == '__main__':
    _test()
