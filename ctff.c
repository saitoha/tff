/*
 * ***** BEGIN LICENSE BLOCK *****
 * Copyright (C) 2012  Hayaki Saito <user@zuse.jp>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 * ***** END LICENSE BLOCK *****
 */

#include <Python.h>
#include <structmember.h>

#include <stdlib.h>
#include <stdint.h>
#include <memory.h>
#include <math.h>


/*****************************************************************************
 *
 * DefaultScanner object
 *
 *****************************************************************************/

/** DefaultScanner object */
typedef struct _DefaultScanner {
    PyObject_HEAD
    char *p_data;
    int length;
    int pos;
    int ucs4;
    PyObject *init_args;
} DefaultScanner;

/** allocator */
static PyObject *
DefaultScanner_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    DefaultScanner *self = (DefaultScanner *)type->tp_alloc(type, 0);
    if (self == NULL) {
        return NULL;
    }
    self->p_data = NULL;
    self->length = 0;
    self->pos = 0;
    self->ucs4 = 0;
    self->init_args = NULL;

    return (PyObject *)self;
}


/** deallocator */
static void
DefaultScanner_dealloc(DefaultScanner *self)
{
    Py_XDECREF(self->init_args);
    self->ob_type->tp_free((PyObject*)self);
}


/** initializer */
static int
DefaultScanner_init(DefaultScanner *self, PyObject *args, PyObject *kwds)
{
    /* Py_INCREF(self); */
    return 0;
}


static PyObject *
DefaultScanner_iter(PyObject *self, PyObject *unused)
{
    Py_INCREF(self);
    return self;
}


static PyObject *
DefaultScanner_next(DefaultScanner *self, PyObject *unused)
{
    long code_point;
    unsigned char c;
    char *p;
    int i, n, length;

    if (self->pos >= self->length) {
        PyErr_SetString(PyExc_StopIteration, "");
        return NULL;
    }

    length = 1;
    p = self->p_data + self->pos;

    c = *p;
    if(~c & 0x80) {
        /* 0xxxxxxx */
        code_point = c;
    goto valid;
    } else if((c & 0xe0) == 0xc0) {
        /* 110xxxxx */
        code_point = c & 0x1F;
        n = 1;
    } else if((c & 0xf0) == 0xe0) {
        /* 1110xxxx */
        code_point = c & 0x0F;
        n = 2;
    } else if((c & 0xf8) == 0xf0) {
        /* 11110xxx */
        code_point = c & 0x07;
        n = 3;
    } else {
        goto invalid;
    }

    for(i = n, ++p; i > 0; --i, ++length, ++p) {
        c = *p;
        if((c & 0xc0) != 0x80) /* 10xxxxxx */
            goto invalid;
        code_point <<= 6;
        code_point |= c & 0x3F;
    }

    if((n == 1 && code_point < 0x80) ||
       (n == 2 && code_point < 0x800) ||
       (n == 3 && code_point < 0x10000) ||
       (code_point >= 0xd800 && code_point <= 0xdfff)) {
        goto invalid;
    }

valid:
    self->pos += length;
    return PyInt_FromLong(code_point);

invalid:
    self->pos += length;
    return PyInt_FromLong(0xfffd);
}

static PyObject *
DefaultScanner_assign(DefaultScanner *self, PyObject *args)
{
    char *termenc = NULL;
    char *p_data = NULL;
    int length = 0;
    int result = 0;

    result = PyArg_ParseTuple(args, "s#s", &p_data, &length, &termenc);
    if (!result) {
        return NULL;
    }

    Py_INCREF(args);
    self->pos = 0;
    self->length = length;
    self->p_data = p_data;

    Py_XDECREF(self->init_args);
    self->init_args = args;

    return Py_None;
}

static PyMethodDef DefaultScanner_methods[] = {
    {"assign", (PyCFunction)DefaultScanner_assign, METH_VARARGS,
     "assign a data chunk" },
    { NULL }  /* Sentinel */
};

/*
 */
static PyMemberDef DefaultScanner_members[] = {
    { "_data", T_STRING, offsetof(DefaultScanner, p_data), READONLY, "" },
    { "_length", T_INT, offsetof(DefaultScanner, length), READONLY, "" },
    { "_ucs4", T_BOOL, offsetof(DefaultScanner, ucs4), READONLY, "" },
    { NULL }  /* Sentinel */
};

static PyTypeObject DefaultScannerType = {
    PyObject_HEAD_INIT(NULL)
    0,                                        /* ob_size           */
    "ctff.DefaultScanner",                    /* tp_name           */
    sizeof(DefaultScanner),                   /* tp_basicsize      */
    0,                                        /* tp_itemsize       */
    (destructor)DefaultScanner_dealloc,       /* tp_dealloc        */
    0,                                        /* tp_print          */
    0,                                        /* tp_getattr        */
    0,                                        /* tp_setattr        */
    0,                                        /* tp_compare        */
    0,                                        /* tp_repr           */
    0,                                        /* tp_as_number      */
    0,                                        /* tp_as_sequence    */
    0,                                        /* tp_as_mapping     */
    0,                                        /* tp_hash           */
    0,                                        /* tp_call           */
    0,                                        /* tp_str            */
    0,                                        /* tp_getattro       */
    0,                                        /* tp_setattro       */
    0,                                        /* tp_as_buffer      */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags          */
    "Default scanner implementation",         /* tp_doc            */
    0,                                        /* tp_traverse       */
    0,                                        /* tp_clear          */
    0,                                        /* tp_richcompare    */
    0,                                        /* tp_weaklistoffset */
    (getiterfunc)DefaultScanner_iter,         /* tp_iter           */
    (iternextfunc)DefaultScanner_next,        /* tp_iternext       */
    DefaultScanner_methods,                   /* tp_methods        */
    DefaultScanner_members,                   /* tp_members        */
    0,                                        /* tp_getset         */
    0,                                        /* tp_base           */
    0,                                        /* tp_dict           */
    0,                                        /* tp_descr_get      */
    0,                                        /* tp_descr_set      */
    0,                                        /* tp_dictoffset     */
    (initproc)DefaultScanner_init,            /* tp_init           */
    0,                                        /* tp_alloc          */
    DefaultScanner_new,                       /* tp_new            */
};

/*****************************************************************************
 *
 * DefaultParser object
 *
 *****************************************************************************/

typedef enum _PARSE_STATE {
    STATE_GROUND = 0,
    STATE_ESC = 1,
    STATE_ESC_INTERMEDIATE = 2,
    STATE_CSI_PARAMETER = 3,
    STATE_CSI_INTERMEDIATE = 4,
    STATE_SS2 = 6,
    STATE_SS3 = 7,
    STATE_OSC = 8,
    STATE_OSC_ESC = 9,
    STATE_STR = 10,
    STATE_STR_ESC = 11
} PARSE_STATE;

static const size_t buf_size = 256;

/** DefaultParser object */
typedef struct _DefaultParser {
    PyObject_HEAD
    PyObject *context;
    PARSE_STATE state;
    PyObject **ibytes;
    size_t ibytes_length;
    PyObject **pbytes;
    size_t pbytes_length;
} DefaultParser;

/** allocator */
static PyObject *
DefaultParser_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    DefaultParser *self = (DefaultParser *)type->tp_alloc(type, 0);
    if (self == NULL) {
        return NULL;
    }

    self->context = NULL;
    self->state = STATE_GROUND;
    self->ibytes = malloc(sizeof(PyObject *) * buf_size);
    self->ibytes_length = 0;
    self->pbytes = malloc(sizeof(PyObject *) * buf_size);
    self->pbytes_length = 0;

    return (PyObject *)self;
}


/** deallocator */
static void
DefaultParser_dealloc(DefaultParser *self)
{
    Py_XDECREF(self->context);
    free(self->ibytes);
    free(self->pbytes);
    self->ob_type->tp_free((PyObject*)self);
}


/** initializer */
static int
DefaultParser_init(DefaultParser *self, PyObject *args, PyObject *kwds)
{
    /* Py_INCREF(self); */
    return 0;
}


static PyObject *
DefaultParser_postinit(DefaultParser *self, PyObject *context)
{
    Py_INCREF(context);
    self->context = context;
    return Py_None;
}


static PyObject *
DefaultParser_state_is_esc(DefaultParser *self)
{
    return self->state == STATE_ESC ? Py_True: Py_False;
}


static PyObject *
DefaultParser_reset(DefaultParser *self)
{
    self->state = STATE_GROUND;
    return Py_None;
}


static PyObject *
DefaultParser_parse(DefaultParser *self, PyObject *data)
{
    PyObject *context = self->context;
    PyObject **ibytes = self->ibytes;
    size_t ibytes_length = self->ibytes_length;
    PyObject **pbytes = self->pbytes;
    size_t pbytes_length = self->pbytes_length;
    PARSE_STATE state = self->state;
    PyObject *iter;
    PyObject *next_char;
    PyObject *seq, *seq2;
    PyObject *assign = PyString_FromString("assign");
    PyObject *dispatch_char = PyString_FromString("dispatch_char");
    PyObject *dispatch_invalid = PyString_FromString("dispatch_invalid");
    PyObject *dispatch_esc = PyString_FromString("dispatch_esc");
    PyObject *dispatch_csi = PyString_FromString("dispatch_csi");
    PyObject *dispatch_control_string = PyString_FromString("dispatch_control_string");
    PyObject *dispatch_ss3 = PyString_FromString("dispatch_ss3");
    PyObject *dispatch_ss2 = PyString_FromString("dispatch_ss2");
    PyObject *code_esc = PyLong_FromLong(0x1b);
    PyObject *code_bracket = PyLong_FromLong(0x5b);
    PyObject *code_o = PyLong_FromLong(0x4f);
    PyObject *code_n = PyLong_FromLong(0x4e);

    long c;
    int i;

    if (!PyObject_CallMethodObjArgs(context, assign, data, NULL)) {
        return NULL;
    }
    iter = PyObject_GetIter(context);
    if (!iter) {
        return NULL;
    }

    while ((next_char = PyIter_Next(iter))) {
        c = PyInt_AS_LONG(next_char);

        if (state == STATE_GROUND) {
            if (c == 0x1b) { /* ESC */
                ibytes_length = 0;
                state = STATE_ESC;
            } else { /* control character */
                if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                    return NULL;
                }
            }
        } else if (state == STATE_ESC) {
            /*
             * - ISO-6429 independent escape sequense
             *
             *     ESC F
             *
             * - ISO-2022 designation sequence
             *
             *     ESC I ... I F
             */
            if (c == 0x5b) { /* [ */
                /*
                    pbytes = []
                    state = _STATE_CSI_PARAMETER
		*/
                pbytes_length = 0;
                state = STATE_CSI_PARAMETER;
            } else if (c == 0x5d) { /* ] */
                pbytes[0] = next_char;
                pbytes_length = 1;
                state = STATE_OSC;
            } else if (c == 0x4e) { /* N */
                state = STATE_SS2;
            } else if (c == 0x4f) { /* O */
                state = STATE_SS3;
            } else if (c == 0x50 || c == 0x58 || c == 0x5e || c == 0x5f) {
                /* P(DCS) or X(SOS) or ^(PM) or _(APC) */
                pbytes[0] = next_char;
                pbytes_length = 1;
                state = STATE_STR;
            } else if (c < 0x20) { /* control character */
                if (c == 0x1b) { /* ESC */
                    seq = PyTuple_Pack(1, code_esc);
                    if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                        return NULL;
                    }
                    ibytes_length = 0;
                    state = STATE_ESC;
                } else if (c == 0x18 || c == 0x1a) {
                    seq = PyTuple_Pack(1, code_esc);
                    if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                        return NULL;
                    }
                    if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                        return NULL;
                    }
                    state = STATE_GROUND;
                } else {
                    if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                        return NULL;
                    }
                }
            } else if (c <= 0x2f) { /* SP to / */
                ibytes[ibytes_length++] = next_char;
                state = STATE_ESC_INTERMEDIATE;
            } else if (c <= 0x7e) { /* ~ */
                PyTuple_New(ibytes_length);
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_esc, seq, next_char, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else if (c == 0x7f) { /* control character */
                if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                    return NULL;
                }
            } else {
                seq = PyTuple_Pack(1, code_esc, next_char);
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            }
        } else if (state == STATE_CSI_PARAMETER) {
            // parse control sequence
            //
            // CSI P ... P I ... I F
            //     ^
            if (c > 0x7e) {
                if (c == 0x7f) { /* control character */
                    if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                        return NULL;
                    }
                } else {
                    seq = PyTuple_New(2 + pbytes_length);
                    PyTuple_SET_ITEM(seq, 0, code_esc);
                    PyTuple_SET_ITEM(seq, 1, code_bracket);
                    for (i = 0; i < pbytes_length; ++i) {
                        PyTuple_SET_ITEM(seq, i + 2, pbytes[i]);
                    }
                    if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                        return NULL;
                    }
                    state = STATE_GROUND;
                }
            } else if (c > 0x3f) { /* Final byte, @ to ~ */
                seq = PyTuple_New(pbytes_length);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, pbytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_csi, seq, PyTuple_New(0), next_char, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else if (c > 0x2f) { /* parameter, 0 to ? */
                pbytes[pbytes_length++] = next_char;
            } else if (c > 0x1f) { /* intermediate, SP to / */
                ibytes[ibytes_length++] = next_char;
                state = STATE_CSI_INTERMEDIATE;
            } else if (c == 0x1b) { /* ESC */
                /* control chars */
                seq = PyTuple_New(2 + pbytes_length);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                PyTuple_SET_ITEM(seq, 1, code_bracket);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2, pbytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                ibytes_length = 0;
                state = STATE_ESC;
            } else if (c == 0x18 || c == 0x1a) { /* CAN, SUB */
                seq = PyTuple_New(2 + pbytes_length);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                PyTuple_SET_ITEM(seq, 1, code_bracket);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2, pbytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else {
                if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                    return NULL;
                }
            }
        } else if (state == STATE_CSI_INTERMEDIATE) {
            // parse control sequence
            //
            // CSI P ... P I ... I F
            //             ^
            if (c > 0x7e) {
                if (c == 0x7f) { /* control character */
                    if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                        return NULL;
                    }
                } else {
                    seq = PyTuple_New(2 + pbytes_length + ibytes_length);
                    PyTuple_SET_ITEM(seq, 0, code_esc);
                    PyTuple_SET_ITEM(seq, 1, code_bracket);
                    for (i = 0; i < pbytes_length; ++i) {
                        PyTuple_SET_ITEM(seq, i + 2, pbytes[i]);
                    }
                    for (i = 0; i < ibytes_length; ++i) {
                        PyTuple_SET_ITEM(seq, i + 2 + pbytes_length, ibytes[i]);
                    }
                    if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                        return NULL;
                    }
                    state = STATE_GROUND;
                }
            } else if (c > 0x3f) { /* Final byte, @ to ~ */
                seq = PyTuple_New(pbytes_length);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2, pbytes[i]);
                }
                seq2 = PyTuple_New(ibytes_length);
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2, ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_csi, seq, seq2, next_char, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else if (c > 0x2f) {
                seq = PyTuple_New(2 + pbytes_length + ibytes_length + 1);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                PyTuple_SET_ITEM(seq, 1, code_bracket);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2, pbytes[i]);
                }
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2 + pbytes_length, ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 2 + pbytes_length + ibytes_length, next_char);
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else if (c > 0x1f) { /* intermediate, SP to / */
                ibytes[ibytes_length++] = next_char;
                state = STATE_CSI_INTERMEDIATE;
            } else if (c == 0x1b) { /* ESC */
                /* control chars */
                seq = PyTuple_New(2 + pbytes_length + ibytes_length);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                PyTuple_SET_ITEM(seq, 1, code_bracket);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2, pbytes[i]);
                }
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2 + pbytes_length, ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                ibytes_length = 0;
                state = STATE_ESC;
            } else if (c == 0x18 || c == 0x1a) {
                seq = PyTuple_New(2 + pbytes_length + ibytes_length);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                PyTuple_SET_ITEM(seq, 1, code_bracket);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2, pbytes[i]);
                }
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2 + pbytes_length, ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else {
                if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                    return NULL;
                }
            }
        } else if (state == STATE_ESC_INTERMEDIATE) {
            if (c > 0x7e) {
                if (c == 0x7f) { /* control character */
                    if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                        return NULL;
                    }
                } else {
                    seq = PyTuple_New(1 + ibytes_length + 1);
                    PyTuple_SET_ITEM(seq, 0, code_esc);
                    for (i = 0; i < ibytes_length; ++i) {
                        PyTuple_SET_ITEM(seq, i + 1, ibytes[i]);
                    }
                    PyTuple_SET_ITEM(seq, 1 + ibytes_length, next_char);
                    if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                        return NULL;
                    }
                    state = STATE_GROUND;
                }
            } else if (c > 0x2f) {  /* 0 to ~, Final byte */
                seq = PyTuple_New(ibytes_length);
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_esc, seq, next_char, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else if (c > 0x1f) { /*  SP to / */
                ibytes[ibytes_length++] = next_char;
                state = STATE_ESC_INTERMEDIATE;
            } else if (c == 0x1b) { /* ESC */
                seq = PyTuple_New(1 + ibytes_length);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, 1 + i, ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                ibytes_length = 0;
                state = STATE_ESC;
            } else if (c == 0x18 || c == 0x1a) {
                seq = PyTuple_New(1 + ibytes_length);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, 1 + i, ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else {
                if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                    return NULL;
                }
            }
        } else if (state == STATE_OSC) {
            /* parse control string */
            if (c == 0x07) {
                seq = PyTuple_New(ibytes_length);
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_control_string, pbytes[0], seq, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else if (c < 0x08) {
                seq = PyTuple_New(1 + pbytes_length + ibytes_length + 1);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1, pbytes[i]);
                }
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1 + pbytes_length, ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 1 + pbytes_length + ibytes_length, next_char);
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else if (c < 0x0e) {
                ibytes[ibytes_length++] = next_char;
            } else if (c == 0x1b) {
                state = STATE_OSC_ESC;
            } else if (c < 0x20) {
                seq = PyTuple_New(1 + pbytes_length + ibytes_length + 1);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1, pbytes[i]);
                }
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1 + pbytes_length, ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 1 + pbytes_length + ibytes_length, next_char);
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else {
                ibytes[ibytes_length++] = next_char;
            }
        } else if (state == STATE_STR) {
            // parse control string
            // 00/08 - 00/13, 02/00 - 07/14
            //
            if (c < 0x08) {
                seq = PyTuple_New(1 + pbytes_length + ibytes_length + 1);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1, pbytes[i]);
                }
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1 + pbytes_length, ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 1 + pbytes_length + ibytes_length, next_char);
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else if (c < 0x0e) {
                ibytes[ibytes_length++] = next_char;
            } else if (c == 0x1b) {
                state = STATE_STR_ESC;
            } else if (c < 0x20) {
                seq = PyTuple_New(1 + pbytes_length + ibytes_length + 1);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1, pbytes[i]);
                }
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1 + pbytes_length, ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 1 + pbytes_length + ibytes_length, next_char);
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else {
                ibytes[ibytes_length++] = next_char;
            }
        } else if (state == STATE_OSC_ESC) {
            /* parse control string */
            if (c == 0x5c) {
                seq = PyTuple_New(ibytes_length);
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_control_string, pbytes[0], seq, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else {
                seq = PyTuple_New(1 + pbytes_length + ibytes_length + 2);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1, pbytes[i]);
                }
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1 + pbytes_length, ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 1 + pbytes_length + ibytes_length, code_esc);
                PyTuple_SET_ITEM(seq, 1 + pbytes_length + ibytes_length + 1, next_char);
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            }
        } else if (state == STATE_STR_ESC) {
            // parse control string
            // 00/08 - 00/13, 02/00 - 07/14
            //
            if (c == 0x5c) {
                seq = PyTuple_New(ibytes_length);
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_control_string, pbytes[0], seq, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else {
                seq = PyTuple_New(1 + pbytes_length + ibytes_length + 2);
                PyTuple_SET_ITEM(seq, 0, code_esc);
                for (i = 0; i < pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1, pbytes[i]);
                }
                for (i = 0; i < ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1 + pbytes_length, ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 1 + pbytes_length + ibytes_length, code_esc);
                PyTuple_SET_ITEM(seq, 1 + pbytes_length + ibytes_length + 1, next_char);
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            }
        } else if (state == STATE_SS3) {
            if (c < 0x20) { /* control character */
                if (c == 0x1b) { /* ESC */
                    seq = PyTuple_Pack(2, code_esc, code_o);
                    if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                        return NULL;
                    }
                    ibytes_length = 0;
                    state = STATE_ESC;
                } else if (c == 0x18 || c == 0x1a) {
                    seq = PyTuple_Pack(2, code_esc, code_o);
                    if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                        return NULL;
                    }
                    if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                        return NULL;
                    }
                    state = STATE_GROUND;
                } else {
                    if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                        return NULL;
                    }
                }
            } else if (c < 0x7f) {
                if (!PyObject_CallMethodObjArgs(context, dispatch_ss3, next_char, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else {
                seq = PyTuple_Pack(2, code_esc, code_o);
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                    return NULL;
                }
            }
        } else if (state == STATE_SS2) {
            if (c < 0x20) { /* control character */
                if (c == 0x1b) { /* ESC */
                    seq = PyTuple_Pack(2, code_esc, code_n);
                    if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                        return NULL;
                    }
                    ibytes_length = 0;
                    state = STATE_ESC;
                } else if (c == 0x18 || c == 0x1a) {
                    seq = PyTuple_Pack(2, code_esc, code_n);
                    if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                        return NULL;
                    }
                    if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                        return NULL;
                    }
                    state = STATE_GROUND;
                } else {
                    if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                        return NULL;
                    }
                }
            } else if (c < 0x7f) {
                if (!PyObject_CallMethodObjArgs(context, dispatch_ss2, next_char, NULL)) {
                    return NULL;
                }
                state = STATE_GROUND;
            } else {
                seq = PyTuple_Pack(2, code_esc, code_o);
                if (!PyObject_CallMethodObjArgs(context, dispatch_invalid, seq, NULL)) {
                    return NULL;
                }
                if (!PyObject_CallMethodObjArgs(context, dispatch_char, next_char, NULL)) {
                    return NULL;
                }
            }
        }
    }
    Py_DECREF(iter);

    self->pbytes = pbytes;
    self->pbytes_length = pbytes_length;
    self->ibytes = ibytes;
    self->ibytes_length = ibytes_length;
    self->state = state;

    return Py_None;
}


static PyMethodDef DefaultParser_methods[] = {
    {"init", (PyCFunction)DefaultParser_postinit, METH_O,
     "assign a context object" },
    {"state_is_esc", (PyCFunction)DefaultParser_state_is_esc, METH_NOARGS,
     "return if parse state is STATE_ESC" },
    {"reset", (PyCFunction)DefaultParser_reset, METH_NOARGS,
     "reset parse state" },
    {"parse", (PyCFunction)DefaultParser_parse, METH_O,
     "do parsing" },
    { NULL }  /* Sentinel */
};

/*
 */
static PyMemberDef DefaultParser_members[] = {
    { NULL }  /* Sentinel */
};

static PyTypeObject DefaultParserType = {
    PyObject_HEAD_INIT(NULL)
    0,                                        /* ob_size           */
    "ctff.DefaultParser",                     /* tp_name           */
    sizeof(DefaultParser),                    /* tp_basicsize      */
    0,                                        /* tp_itemsize       */
    (destructor)DefaultParser_dealloc,        /* tp_dealloc        */
    0,                                        /* tp_print          */
    0,                                        /* tp_getattr        */
    0,                                        /* tp_setattr        */
    0,                                        /* tp_compare        */
    0,                                        /* tp_repr           */
    0,                                        /* tp_as_number      */
    0,                                        /* tp_as_sequence    */
    0,                                        /* tp_as_mapping     */
    0,                                        /* tp_hash           */
    0,                                        /* tp_call           */
    0,                                        /* tp_str            */
    0,                                        /* tp_getattro       */
    0,                                        /* tp_setattro       */
    0,                                        /* tp_as_buffer      */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags          */
    "Default parser implementation",          /* tp_doc            */
    0,                                        /* tp_traverse       */
    0,                                        /* tp_clear          */
    0,                                        /* tp_richcompare    */
    0,                                        /* tp_weaklistoffset */
    0,                                        /* tp_iter           */
    0,                                        /* tp_iternext       */
    DefaultParser_methods,                    /* tp_methods        */
    DefaultParser_members,                    /* tp_members        */
    0,                                        /* tp_getset         */
    0,                                        /* tp_base           */
    0,                                        /* tp_dict           */
    0,                                        /* tp_descr_get      */
    0,                                        /* tp_descr_set      */
    0,                                        /* tp_dictoffset     */
    (initproc)DefaultParser_init,             /* tp_init           */
    0,                                        /* tp_alloc          */
    DefaultParser_new,                        /* tp_new            */
};


/*
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
*/

static char ctff_doc[] = "Terminal filter framework C implementation part.\n";

static PyMethodDef methods[] = {
    { NULL, NULL, 0, NULL}
};

/** module entry point */
extern void initctff(void)
{
    PyObject *m;

    m = Py_InitModule3("ctff", methods, ctff_doc);

    if (PyType_Ready(&DefaultScannerType) < 0) {
        return;
    }
    PyModule_AddObject(m, "DefaultScanner", (PyObject *)&DefaultScannerType);

    if (PyType_Ready(&DefaultParserType) < 0) {
        return;
    }
    PyModule_AddObject(m, "DefaultParser", (PyObject *)&DefaultParserType);
}

// EOF
