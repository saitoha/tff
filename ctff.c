/*
 * ***** BEGIN LICENSE BLOCK *****
 * Copyright (C) 2012-2014, Hayaki Saito 
 * 
 * Permission is hereby granted, free of charge, to any person obtaining a 
 * copy of this software and associated documentation files (the "Software"), 
 * to deal in the Software without restriction, including without limitation 
 * the rights to use, copy, modify, merge, publish, distribute, sublicense, 
 * and/or sell copies of the Software, and to permit persons to whom the 
 * Software is furnished to do so, subject to the following conditions: 
 * 
 * The above copyright notice and this permission notice shall be included in 
 * all copies or substantial portions of the Software. 
 * 
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL 
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
 * DEALINGS IN THE SOFTWARE. 
 * 
 * ***** END LICENSE BLOCK *****
 */

/*
#define TFF_USE_PTHREAD 1
*/

#include <Python.h>
#include <structmember.h>

#if defined(TFF_USE_PTHREAD)
#  include <pthread.h>
#endif

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
        if((c & 0xc0) != 0x80) {
            /* 10xxxxxx */
            goto invalid;
        }
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
#if defined(TFF_USE_PTHREAD)
    pthread_mutex_t mutex;
#endif
} DefaultParser;

PyObject *str_assign;
PyObject *str_dispatch_char;
PyObject *str_dispatch_invalid;
PyObject *str_dispatch_esc;
PyObject *str_dispatch_csi;
PyObject *str_dispatch_control_string;
PyObject *str_dispatch_ss3;
PyObject *str_dispatch_ss2;
PyObject *str_code_esc;
PyObject *str_code_bracket;
PyObject *str_code_o;
PyObject *str_code_n;
PyObject *seq_empty;

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
#if defined(TFF_USE_PTHREAD)
    pthread_mutex_init(&self->mutex, 0);
#endif
    return (PyObject *)self;
}


/** deallocator */
static void
DefaultParser_dealloc(DefaultParser *self)
{
    free(self->ibytes);
    free(self->pbytes);
#if defined(TFF_USE_PTHREAD)
    pthread_mutex_destroy(&self->mutex);
#endif
    self->ob_type->tp_free((PyObject*)self);
}


/** initializer */
static int
DefaultParser_init(DefaultParser *self, PyObject *args, PyObject *kwds)
{
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
    PyObject *iter;
    PyObject *next_char;
    PyObject *seq, *seq2;
    long c;
    int i;

#if defined(TFF_USE_PTHREAD)
    pthread_mutex_lock(&self->mutex);
#endif

    if (!PyObject_CallMethodObjArgs(self->context, str_assign, data, NULL)) {
        return NULL;
    }

    iter = PyObject_GetIter(self->context);
    if (!iter) {
        return NULL;
    }

    while ((next_char = PyIter_Next(iter))) {

        c = PyInt_AS_LONG(next_char);
        if (self->state == STATE_GROUND) {
            if (c == 0x1b) { /* ESC */
                self->ibytes_length = 0;
                self->state = STATE_ESC;
            } else {
		/* character */
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                    goto error;
                }
            }
        } else if (self->state == STATE_ESC) {
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
                 *   pbytes = []
                 *   state = _STATE_CSI_PARAMETER
                 */
                self->pbytes_length = 0;
                self->state = STATE_CSI_PARAMETER;
            } else if (c == 0x5d) { /* ] */
                self->pbytes[0] = next_char;
                self->pbytes_length = 1;
                self->state = STATE_OSC;
            } else if (c == 0x4e) { /* N */
                self->state = STATE_SS2;
            } else if (c == 0x4f) { /* O */
                self->state = STATE_SS3;
            } else if (c == 0x50 || c == 0x58 || c == 0x5e || c == 0x5f) {
                /* P(DCS) or X(SOS) or ^(PM) or _(APC) */
                self->pbytes[0] = next_char;
                self->pbytes_length = 1;
                self->state = STATE_STR;
            } else if (c < 0x20) { /* control character */
                if (c == 0x1b) { /* ESC */
                    seq = PyTuple_Pack(1, str_code_esc);
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                        goto error;
                    }
                    self->ibytes_length = 0;
                    self->state = STATE_ESC;
                } else if (c == 0x18 || c == 0x1a) {
                    seq = PyTuple_Pack(1, str_code_esc);
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                        goto error;
                    }
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                        goto error;
                    }
                    self->state = STATE_GROUND;
                } else {
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                        goto error;
                    }
                }
            } else if (c <= 0x2f) { /* SP to / */
                self->ibytes[self->ibytes_length++] = next_char;
                self->state = STATE_ESC_INTERMEDIATE;
            } else if (c <= 0x7e) { /* ~ */
                seq = PyTuple_New(self->ibytes_length);
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, self->ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_esc, seq, next_char, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else if (c == 0x7f) { /* control character */
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                    goto error;
                }
            } else {
                seq = PyTuple_Pack(1, str_code_esc, next_char);
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            }
        } else if (self->state == STATE_CSI_PARAMETER) {
            /*
             * parse control sequence
            
             * CSI P ... P I ... I F
             *     ^
             */
            if (c > 0x7e) {
                if (c == 0x7f) { /* control character */
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                        goto error;
                    }
                } else {
                    seq = PyTuple_New(2 + self->pbytes_length);
                    PyTuple_SET_ITEM(seq, 0, str_code_esc);
                    PyTuple_SET_ITEM(seq, 1, str_code_bracket);
                    for (i = 0; i < self->pbytes_length; ++i) {
                        PyTuple_SET_ITEM(seq, i + 2, self->pbytes[i]);
                    }
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                        goto error;
                    }
                    self->state = STATE_GROUND;
                }
            } else if (c > 0x3f) { /* Final byte, @ to ~ */
                seq = PyTuple_New(self->pbytes_length);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, self->pbytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_csi, seq, seq_empty, next_char, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else if (c > 0x2f) { /* parameter, 0 to ? */
                self->pbytes[self->pbytes_length++] = next_char;
            } else if (c > 0x1f) { /* intermediate, SP to / */
                self->ibytes[self->ibytes_length++] = next_char;
                self->state = STATE_CSI_INTERMEDIATE;
            } else if (c == 0x1b) { /* ESC */
                /* control chars */
                seq = PyTuple_New(2 + self->pbytes_length);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                PyTuple_SET_ITEM(seq, 1, str_code_bracket);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2, self->pbytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                self->ibytes_length = 0;
                self->state = STATE_ESC;
            } else if (c == 0x18 || c == 0x1a) { /* CAN, SUB */
                seq = PyTuple_New(2 + self->pbytes_length);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                PyTuple_SET_ITEM(seq, 1, str_code_bracket);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2, self->pbytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else {
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                    goto error;
                }
            }
        } else if (self->state == STATE_CSI_INTERMEDIATE) {
            /*
             * parse control sequence
             *
             * CSI P ... P I ... I F
             *             ^
             */
            if (c > 0x7e) {
                if (c == 0x7f) {
                    /* control character */
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                        goto error;
                    }
                } else {
                    seq = PyTuple_New(2 + self->pbytes_length + self->ibytes_length);
                    PyTuple_SET_ITEM(seq, 0, str_code_esc);
                    PyTuple_SET_ITEM(seq, 1, str_code_bracket);
                    for (i = 0; i < self->pbytes_length; ++i) {
                        PyTuple_SET_ITEM(seq, i + 2, self->pbytes[i]);
                    }
                    for (i = 0; i < self->ibytes_length; ++i) {
                        PyTuple_SET_ITEM(seq, i + 2 + self->pbytes_length, self->ibytes[i]);
                    }
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                        goto error;
                    }
                    self->state = STATE_GROUND;
                }
            } else if (c > 0x3f) { /* Final byte, @ to ~ */
                seq = PyTuple_New(self->pbytes_length);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, self->pbytes[i]);
                }
                seq2 = PyTuple_New(self->ibytes_length);
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, self->ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_csi, seq, seq2, next_char, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else if (c > 0x2f) {
                seq = PyTuple_New(2 + self->pbytes_length + self->ibytes_length + 1);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                PyTuple_SET_ITEM(seq, 1, str_code_bracket);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2, self->pbytes[i]);
                }
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2 + self->pbytes_length, self->ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 2 + self->pbytes_length + self->ibytes_length, next_char);
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else if (c > 0x1f) { /* intermediate, SP to / */
                self->ibytes[self->ibytes_length++] = next_char;
                self->state = STATE_CSI_INTERMEDIATE;
            } else if (c == 0x1b) { /* ESC */
                /* control chars */
                seq = PyTuple_New(2 + self->pbytes_length + self->ibytes_length);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                PyTuple_SET_ITEM(seq, 1, str_code_bracket);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2, self->pbytes[i]);
                }
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2 + self->pbytes_length, self->ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                self->ibytes_length = 0;
                self->state = STATE_ESC;
            } else if (c == 0x18 || c == 0x1a) {
                seq = PyTuple_New(2 + self->pbytes_length + self->ibytes_length);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                PyTuple_SET_ITEM(seq, 1, str_code_bracket);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2, self->pbytes[i]);
                }
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 2 + self->pbytes_length, self->ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else {
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                    goto error;
                }
            }
        } else if (self->state == STATE_ESC_INTERMEDIATE) {
            if (c > 0x7e) {
                if (c == 0x7f) { /* control character */
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                        goto error;
                    }
                } else {
                    seq = PyTuple_New(1 + self->ibytes_length + 1);
                    PyTuple_SET_ITEM(seq, 0, str_code_esc);
                    for (i = 0; i < self->ibytes_length; ++i) {
                        PyTuple_SET_ITEM(seq, i + 1, self->ibytes[i]);
                    }
                    PyTuple_SET_ITEM(seq, 1 + self->ibytes_length, next_char);
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                        goto error;
                    }
                    self->state = STATE_GROUND;
                }
            } else if (c > 0x2f) {  /* 0 to ~, Final byte */
                seq = PyTuple_New(self->ibytes_length);
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, self->ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_esc, seq, next_char, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else if (c > 0x1f) { /*  SP to / */
                self->ibytes[self->ibytes_length++] = next_char;
                self->state = STATE_ESC_INTERMEDIATE;
            } else if (c == 0x1b) { /* ESC */
                seq = PyTuple_New(1 + self->ibytes_length);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, 1 + i, self->ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                self->ibytes_length = 0;
                self->state = STATE_ESC;
            } else if (c == 0x18 || c == 0x1a) {
                seq = PyTuple_New(1 + self->ibytes_length);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, 1 + i, self->ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else {
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                    goto error;
                }
            }
        } else if (self->state == STATE_OSC) {
            /* parse control string */
            if (c == 0x07) {
                seq = PyTuple_New(self->ibytes_length);
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, self->ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_control_string, *self->pbytes, seq, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else if (c < 0x08) {
                seq = PyTuple_New(1 + self->pbytes_length + self->ibytes_length + 1);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1, self->pbytes[i]);
                }
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1 + self->pbytes_length, self->ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 1 + self->pbytes_length + self->ibytes_length, next_char);
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else if (c < 0x0e) {
                self->ibytes[self->ibytes_length++] = next_char;
            } else if (c == 0x1b) {
                self->state = STATE_OSC_ESC;
            } else if (c < 0x20) {
                seq = PyTuple_New(1 + self->pbytes_length + self->ibytes_length + 1);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1, self->pbytes[i]);
                }
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1 + self->pbytes_length, self->ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 1 + self->pbytes_length + self->ibytes_length, next_char);
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else {
                self->ibytes[self->ibytes_length++] = next_char;
            }
        } else if (self->state == STATE_STR) {
            /*
             * parse control string
             * 00/08 - 00/13, 02/00 - 07/14
             */
            if (c < 0x08) {
                seq = PyTuple_New(1 + self->pbytes_length + self->ibytes_length + 1);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1, self->pbytes[i]);
                }
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1 + self->pbytes_length, self->ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 1 + self->pbytes_length + self->ibytes_length, next_char);
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else if (c < 0x0e) {
                self->ibytes[self->ibytes_length++] = next_char;
            } else if (c == 0x1b) {
                self->state = STATE_STR_ESC;
            } else if (c < 0x20) {
                seq = PyTuple_New(1 + self->pbytes_length + self->ibytes_length + 1);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1, self->pbytes[i]);
                }
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1 + self->pbytes_length, self->ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 1 + self->pbytes_length + self->ibytes_length, next_char);
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else {
                self->ibytes[self->ibytes_length++] = next_char;
            }
        } else if (self->state == STATE_OSC_ESC) {
            /* parse control string */
            if (c == 0x5c) {
                seq = PyTuple_New(self->ibytes_length);
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, self->ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_control_string, *self->pbytes, seq, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else {
                seq = PyTuple_New(1 + self->pbytes_length + self->ibytes_length + 2);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1, self->pbytes[i]);
                }
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1 + self->pbytes_length, self->ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 1 + self->pbytes_length + self->ibytes_length, str_code_esc);
                PyTuple_SET_ITEM(seq, 1 + self->pbytes_length + self->ibytes_length + 1, next_char);
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            }
        } else if (self->state == STATE_STR_ESC) {
            /*
             * parse control string
             * 00/08 - 00/13, 02/00 - 07/14
             */
            if (c == 0x5c) {
                seq = PyTuple_New(self->ibytes_length);
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i, self->ibytes[i]);
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_control_string, *self->pbytes, seq, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else {
                seq = PyTuple_New(1 + self->pbytes_length + self->ibytes_length + 2);
                PyTuple_SET_ITEM(seq, 0, str_code_esc);
                for (i = 0; i < self->pbytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1, self->pbytes[i]);
                }
                for (i = 0; i < self->ibytes_length; ++i) {
                    PyTuple_SET_ITEM(seq, i + 1 + self->pbytes_length, self->ibytes[i]);
                }
                PyTuple_SET_ITEM(seq, 1 + self->pbytes_length + self->ibytes_length, str_code_esc);
                PyTuple_SET_ITEM(seq, 1 + self->pbytes_length + self->ibytes_length + 1, next_char);
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            }
        } else if (self->state == STATE_SS3) {
            if (c < 0x20) { /* control character */
                if (c == 0x1b) { /* ESC */
                    seq = PyTuple_Pack(2, str_code_esc, str_code_o);
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                        goto error;
                    }
                    self->ibytes_length = 0;
                    self->state = STATE_ESC;
                } else if (c == 0x18 || c == 0x1a) {
                    seq = PyTuple_Pack(2, str_code_esc, str_code_o);
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                        goto error;
                    }
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                        goto error;
                    }
                    self->state = STATE_GROUND;
                } else {
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                        goto error;
                    }
                }
            } else if (c < 0x7f) {
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_ss3, next_char, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else {
                seq = PyTuple_Pack(2, str_code_esc, str_code_o);
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                    goto error;
                }
            }
        } else if (self->state == STATE_SS2) {
            if (c < 0x20) { /* control character */
                if (c == 0x1b) { /* ESC */
                    seq = PyTuple_Pack(2, str_code_esc, str_code_n);
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                        goto error;
                    }
                    self->ibytes_length = 0;
                    self->state = STATE_ESC;
                } else if (c == 0x18 || c == 0x1a) {
                    seq = PyTuple_Pack(2, str_code_esc, str_code_n);
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                        goto error;
                    }
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                        goto error;
                    }
                    self->state = STATE_GROUND;
                } else {
                    if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                        goto error;
                    }
                }
            } else if (c < 0x7f) {
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_ss2, next_char, NULL)) {
                    goto error;
                }
                self->state = STATE_GROUND;
            } else {
                seq = PyTuple_Pack(2, str_code_esc, str_code_o);
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_invalid, seq, NULL)) {
                    goto error;
                }
                if (!PyObject_CallMethodObjArgs(self->context, str_dispatch_char, next_char, NULL)) {
                    goto error;
                }
            }
        }
        Py_DECREF(next_char);
    }

    Py_DECREF(iter);

#if defined(TFF_USE_PTHREAD)
    pthread_mutex_unlock(&self->mutex);
#endif

    if (PyErr_Occurred()) {
        return NULL;
    }
    return Py_None;
error:
#if defined(TFF_USE_PTHREAD)
    pthread_mutex_unlock(&self->mutex);
#endif
    Py_DECREF(next_char);
    Py_DECREF(iter);
    return NULL;
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

    str_assign = PyString_FromString("assign");
    str_dispatch_char = PyString_FromString("dispatch_char");
    str_dispatch_invalid = PyString_FromString("dispatch_invalid");
    str_dispatch_esc = PyString_FromString("dispatch_esc");
    str_dispatch_csi = PyString_FromString("dispatch_csi");
    str_dispatch_control_string = PyString_FromString("dispatch_control_string");
    str_dispatch_ss3 = PyString_FromString("dispatch_ss3");
    str_dispatch_ss2 = PyString_FromString("dispatch_ss2");
    str_code_esc = PyLong_FromLong(0x1b);
    str_code_bracket = PyLong_FromLong(0x5b);
    str_code_o = PyLong_FromLong(0x4f);
    str_code_n = PyLong_FromLong(0x4e);
    seq_empty = PyTuple_New(0);

    if (PyType_Ready(&DefaultParserType) < 0) {
        return;
    }
    PyModule_AddObject(m, "DefaultParser", (PyObject *)&DefaultParserType);
}

/* EOF */
