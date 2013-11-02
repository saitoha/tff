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
}

// EOF
