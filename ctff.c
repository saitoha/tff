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

    return (PyObject *)self;
}
 
/** deallocator */
static void
DefaultScanner_dealloc(DefaultScanner *self)
{
    if (self->p_data) {
        free(self->p_data);
        self->p_data = NULL;
    }

    self->ob_type->tp_free((PyObject*)self);
}

/** initializer */
static int
DefaultScanner_init(DefaultScanner *self, PyObject *args, PyObject *kwds)
{
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
    unsigned char c0, c1, c2, c3, c4;

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
    return Py_None;
}

static PyObject *
DefaultScanner_assign(PyObject *self, PyObject *args)
{
    PyTypeObject *type;
    DefaultScanner *p_scanner;

    p_scanner = (DefaultScanner *)self;

    if (!PyArg_ParseTuple(args, "s#", &p_scanner->p_data, &p_scanner->length)) {
        return NULL;
    }

    return 0;
}

static PyMethodDef DefaultScanner_methods[] = {
    {"chunk", DefaultScanner_assign, METH_VARARGS, "assign a data chunk" },
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
    0,                                        /* tp_iternext       */
    DefaultScanner_methods,                   /* tp_methods        */
    0,                                        /* tp_members        */
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
