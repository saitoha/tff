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

    return (PyObject *)self;
}
 
/** deallocator */
static void
DefaultScanner_dealloc(DefaultScanner *self)
{
    /* self->p_data is narrowed reference */

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
DefaultScanner_self(DefaultScanner *self, PyObject *unused)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject *
DefaultScanner_next(DefaultScanner *self, PyObject *unused)
{
    PyObject *row;
    unsigned char c0, c1;//, c2, c3, c4;

    Py_INCREF(self);

    if (self->pos == self->length) {
        PyErr_SetString(PyExc_StopIteration, "");
        return NULL;
    }

    c0 = (unsigned char)self->p_data[self->pos++];

    if (c0 < 0x7f) {
        return PyInt_FromLong(c0);
    } else if (c0 < 0xc2) {
    } else if (c0 < 0xdf) {
        c1 = (unsigned char)self->p_data[self->pos++];
        if (c1) {
        }
    } 

    Py_DECREF(self);

    return Py_None;
}

static PyObject *
DefaultScanner_assign(PyObject *self, PyObject *args)
{
    PyTypeObject *type;
    DefaultScanner *p_scanner;

    p_scanner = (DefaultScanner *)self;

    Py_INCREF(p_scanner);

    assert(p_scanner != NULL);

    if (!PyArg_ParseTuple(args, "s#", &p_scanner->p_data, &p_scanner->length)) {

        Py_DECREF(p_scanner);

        return NULL;
    }

    Py_DECREF(p_scanner);

    return Py_None;
}

static PyMethodDef DefaultScanner_methods[] = {
    {"assign", DefaultScanner_assign, METH_VARARGS, "assign a data chunk" },
    { NULL }  /* Sentinel */
};

/*
 */
static PyMemberDef DefaultScanner_members[] = {
    { "_ucs4", T_BOOL, offsetof(DefaultScanner, ucs4), 0, "" },
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
    0,                                        /* tp_iter           */
    DefaultScanner_next,                      /* tp_iternext       */
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
