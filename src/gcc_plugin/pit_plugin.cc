/*!
 * \file pit_plugin.cc
 * \brief PIT main source file
 */

#ifndef _GNU_SOURCE
#define _GNU_SOURCE // Required to use asprintf()
#endif

#include <iostream>
#include <json-c/json.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

// clang-format off
// GCC headers, the order is important.
#include "gcc-plugin.h"
#include "plugin-version.h"
#include "tree-pass.h"
#include "context.h"
#include "function.h"
#include "tree.h"
#include "tree-ssa-alias.h"
#include "internal-fn.h"
#include "is-a.h"
#include "predict.h"
#include "basic-block.h"
#include "gimple-expr.h"
#include "gimple.h"
#include "gimple-pretty-print.h"
#include "gimple-iterator.h"
#include "gimple-walk.h"
#include "cgraph.h"
#include "tree-iterator.h"
#include "langhooks.h"
#include <libgen.h>
#include <libiberty.h>
#include <print-tree.h>
#include "line-map.h"
#include "c-tree.h"
// clang-format on

#define I_STRUCT			0
#define I_LOC_PRE			2

#define VAR_FUNCTION_OR_PARM_DECL_CHECK(NODE)                                  \
	TREE_CHECK3(NODE, VAR_DECL, FUNCTION_DECL, PARM_DECL)

#define DECL_THIS_EXTERN(NODE)                                                 \
	DECL_LANG_FLAG_2(VAR_FUNCTION_OR_PARM_DECL_CHECK(NODE))

#define NODE_DECL(node) (node)->decl

// We must assert that this plugin is GPL compatible
int plugin_is_GPL_compatible;

static struct plugin_info pic_gcc_plugin_info = {"1.0", "PIC plugin"};

struct gcc_variable {
	struct varpool_node *inner;
};

typedef struct gcc_variable gcc_variable;

static FILE *log_fd;                       /** \brief fd for logging */
static const char *cur_func = NULL;        /** \brief current function name */
static const char *cur_file = NULL;        /** \brief current file name */
static char *base_path = NULL;             /** \brief source base code path */
static char *out_path = NULL;              /** \brief output data path */
json_object *struct_obj;
json_object *struct_lst;

/* Global result structure */

json_object *data_decl = NULL;
json_object *data_stmt = NULL;
json_object *data_struct = NULL;
json_object *data_dlen = NULL;
json_object *data_flen = NULL;
json_object *data_pre = NULL;
json_object *data_ustruct = NULL;






/*! Check if file exists
 *  @param name file name to be checked if exists
 */
static inline bool f_exists(const char *name)
{
	struct stat buffer;
	return (stat(name, &buffer) == 0);
}


/*! Check if directory exists
 *  @param name directory name to be checked if exists
 */
static inline bool d_exists(const char *dir)
{
	struct stat sb;
	return (stat(dir, &sb) == 0 && S_ISDIR(sb.st_mode));
}


/*!Function to parse path from param fpath
 * @param fpath   file name path to be parsed
 *
 * */
static char *get_path(char *fpath)
{
	char *dpath, *opath;

	dpath = xstrdup(fpath);
	opath = xstrdup(dirname(dpath));
	free(dpath);

	return opath;
}




/*! Check if str is in json array
 * @param obj  json array.
 * @param str  string to be checked.
 *
 */
static bool in_jarray(json_object *obj, const char *str)
{
	int i;
	int len;
	json_object *_obj;
	len = json_object_array_length(obj);

	for (i = 0; i < len; i++) {
		const char *_str;

		_obj = json_object_array_get_idx(obj, i);
		_str = json_object_get_string(_obj);
		if (!strcmp(_str, str))
			return true;
	}
	return false;
}

/*!Check if int is in json array
 *
 * @param obj  json array
 * @param int  integer to be checked
 *
 * */
static bool int_in_jarray(json_object *obj, int val)
{
	int i;
	int len;
	json_object *_obj;
	len = json_object_array_length(obj);

	for (i = 0; i < len; i++) {
		int _val;

		_obj = json_object_array_get_idx(obj, i);
		_val = json_object_get_int(_obj);
		if (_val == val)
			return true;
	}
	return false;
}

/*!Check if json dict has string key
 *
 * @param obj  json dict
 * @param str  string to be checked
 *
 * */
static bool has_skey(json_object *obj, const char *str)
{
	json_object *sobj;
	json_object_object_get_ex(obj, str, &sobj);

	if (sobj == NULL)
		return false;
	else
		return true;
}


/*! Set json object for certain key
 *
 * @param obj       json object we are set data
 * @param key_name  json dictionary key name
 * @param tok
 *
 * return   true, there is no return to check for
 *                json_object_object_add
 * */
static bool json_set_key(json_object *obj, const char * key_name, json_object *tok)
{
    int ret;
	json_object *mtok;

    /* Get if available object form main object list */
    ret = json_object_object_get_ex(obj, key_name, &mtok);

    if (ret == 1)
        mtok = tok;
    else
        json_object_object_add(obj, key_name, tok);

    return true;
}

/*! Get json object for certain key
 *
 * @param obj       json object we are serching in
 * @param key_name  json dictionary key name we are search for
 *
 * return   object if found or NULL
 * */
json_object *json_get_key(json_object *obj, const char * key_name)
{
    int ret;
	json_object *mtok;

    /* Get if available object form main object list */
	ret = json_object_object_get_ex(obj, key_name, &mtok);

	if (ret == 1)
        return mtok;
	else
	    return NULL;
}

/*!Read json file from disk
 *
 * @param fname   file name of json file to be read
 *
 * */
static json_object *read_json(const char *fname)
{
	FILE *fp;
	int bufsize;
	char *contents;
	json_object *obj = NULL;

	if (!f_exists(fname)) {
		/* fprintf(stderr, "%s:%d The file: %s does not exists\n",
		 * __FUNCTION__, __LINE__, fname); */
		return NULL;
	}

	fp = fopen(fname, "r");
	if (fp == NULL) {
		perror("Error read data from json\n");
		return NULL;
	}

	if (fseek(fp, 0L, SEEK_END) != 0) {
		perror("Could not seek the end of the file\n");
		goto error;
	}

	// Get the size of the file.
	bufsize = ftell(fp);
	if (bufsize == -1) {
		perror("ftell failed\n");
		goto ftell_error;
	}

	contents = (char *)xcalloc(sizeof(char), bufsize + 1);
	if (fseek(fp, 0L, SEEK_SET) != 0) {
		perror("Seek failed\n");
		goto fseek_error;
	}

	if (fread(contents, sizeof(char), bufsize, fp) == 0) {
		fprintf(stderr, "Error reading file: %s", fname);
		goto fread_error;
	}

	obj = json_tokener_parse(contents);

fread_error:
fseek_error:
	free(contents);
ftell_error:
error:
	fclose(fp);
	return obj;
}


/*!Create a directory
 *
 * @param path  path to be created
 *
 * */
static int pit_mkdir(const char *path)
{
	int ret;
	char *begin, *end;

	begin = (char *)path;
	begin++;
	while ((end = strchr(begin, '/'))) {
		char aux[PATH_MAX] = {};
		if (!memcpy(aux, path, end - path))
			return -1;

		ret = mkdir(aux, 0755);
		begin = end + 1;

		if (ret == -1) {
			if (errno == EEXIST)
				continue;

			return -1;
		}
	}

	ret = mkdir(path, 0755);
	if (ret == -1) {
		if (errno != EEXIST)
			return -1;
	}

	return 0;
}



/*!Function to save information about a global variable
 *
 * @param fname      file name of json file to be written
 * @param name       global variable name
 * @param type       variable type
 * @param exported   flag if variable has been exported
 * @param line       global variable line number information
 *
 * */
static int save_global(const char *fname, const char *name, const char *type,
		       unsigned int exported, int line)
{
	FILE *fp;
	char full_path[PATH_MAX] = {}, *path;
	int ret;
	json_object *sobj, *jobj = NULL;
	size_t base_len = strlen(base_path);

	if (fname == NULL)
		return 0;

	ret = strncmp(fname, base_path, base_len);
	if (ret == 0) {
		size_t len_base = strlen(base_path);
		size_t len_path = strlen(fname);

		ret = snprintf(full_path, sizeof(full_path), "%s/%.*s.gl",
			       out_path, (int)(len_path - len_base),
			       fname + len_base);
	} else {
		ret = snprintf(full_path, sizeof(full_path), "%s/%s.gl",
			       out_path, fname);
	}

	if ((ret < 0) || (ret >= PATH_MAX))
		return -1;

	path = get_path(full_path);
	if (!d_exists(path)) {
		ret = pit_mkdir(path);
	}
	free(path);

	if (ret == -1)
		return -1;

	sobj = json_object_new_object();
	if (sobj == NULL) {
		fprintf(stderr, "%s:%d - Could not create json object\n",
			__FUNCTION__, __LINE__);
		return -1;
	}

#define CREATE_OBJECT_AND_ADD(_function, _param, _str)                         \
	do {                                                                   \
		json_object *_obj;                                             \
		_obj = _function(_param);                                      \
		if (_obj == NULL) {                                            \
			fprintf(stderr,                                        \
				"%s:%d - Could not create json_object\n",      \
				__FUNCTION__, __LINE__);                       \
			goto error;                                            \
		}                                                              \
		json_object_object_add(sobj, _str, _obj);                      \
	} while (0)

	CREATE_OBJECT_AND_ADD(json_object_new_int, line, "line");
	CREATE_OBJECT_AND_ADD(json_object_new_boolean, exported, "public");
	CREATE_OBJECT_AND_ADD(json_object_new_string, type, "type");
#undef CREATE_OBJECT_AND_ADD

	if (!f_exists(full_path)) {
		jobj = json_object_new_object();
		if (jobj == NULL) {
			fprintf(stderr,
				"%s:%d - Could not create json object\n",
				__FUNCTION__, __LINE__);
			goto error;
		}
		json_object_object_add(jobj, name, sobj);
	} else {
		jobj = read_json(full_path);
		if (jobj == NULL) {
			fprintf(stderr, "%s:%d - Could not get tokens\n",
				__FUNCTION__, __LINE__);
			goto error;
		}
		json_object_object_add(jobj, name, sobj);
	}

	fp = fopen(full_path, "w");
	if (fp == NULL) {
		perror("Open json file failed\n");
		json_object_put(jobj);
		return -1;
	}

	fprintf(fp, "%s", json_object_to_json_string(jobj));
	fclose(fp);
	json_object_put(jobj);
	return 0;

error:
	json_object_put(sobj);
	return -1;
}

/*! Generate key for certain file name
 *
 * @param obj       file name
 * @param key_name  a suffix we want to attach (stmt, flen, dlen ...)
 *
 * */
static char *key_from_path(const char *fname, const char *suffix)
{
    int ret;
    //char file_name[PATH_MAX] = {}, *path;
    char *file_name = NULL;
    char *ptr;

    ptr = (char *)fname;

	ret = strncmp(fname, "./", strlen("./"));
    if (strncmp(fname, "./", strlen("./")) == 0) {
        ptr = ptr + strlen("./");
        ret = asprintf(&file_name, "%s.%s", ptr, suffix);
    }
    else if (strncmp(fname, base_path, strlen(base_path)) == 0) {
        ptr = ptr + strlen(out_path) + 1;
        ret = sprintf(file_name, "%s.%s", ptr, suffix);
	} else {
		ret = asprintf(&file_name, "%s.%s", fname, suffix);
	}
	if ((ret < 0) || (ret >= PATH_MAX))
		return NULL;

    return file_name;
}


/*!used to write information of structure, declaration function body length
 *
 * @param type    file name suffix
 * @param fname   file name
 * @param name    function or structure name
 * @param start   start line number location
 * @param end     end line number location
 *
 */
static int dump_data(json_object *obj, const char *fname,
                            const char *name, int start, int end)
{
	json_object *j_start, *j_sobj, *j_cu;

    if (!has_skey(obj, fname)){
	    j_cu = json_object_new_object();
         /* should not be needed, done in json_set_key
          * json_set_key(obj, fname, j_cu); */
    }
    else{
        j_cu = json_get_key(obj, fname);
        if (j_cu == NULL){
            fprintf(stderr, "Error\n");
			json_object_put(j_cu);
        }
    }

	j_sobj = json_object_new_object();
	if (j_sobj == NULL) {
		fprintf(stderr, "%s:%d - Could not create json object\n",
			__FUNCTION__, __LINE__);
		goto err;
	}

	j_start = json_object_new_int(start);
	if (j_start == NULL) {
		fprintf(stderr, "%s:%d - Could not create json object\n",
			__FUNCTION__, __LINE__);
		goto err;
	}

	json_object_object_add(j_sobj, "start", j_start);
	if (end != -1) {
		json_object *j_end = json_object_new_int(end);
		if (j_end == NULL) {
			fprintf(stderr,
				"%s:%d - Could not create json object\n",
				__FUNCTION__, __LINE__);
			goto err;
		}
		json_object_object_add(j_sobj, "end", j_end);
	}

	json_object_object_add(j_cu, name, j_sobj);
    json_set_key(obj, fname, j_cu); // PPP

	return 0;

err:
	json_object_put(j_sobj);
	return -1;
}

namespace
{
const pass_data get_stmt_pass_data = {
    GIMPLE_PASS,
    "get_smtm_pass",    // name
    OPTGROUP_NONE,      // optinfo_flags
    TV_NONE,            // tv_id
    PROP_gimple_any,    // properties_required
    0,                  // properties_provided
    0,                  // properties_destroyed
    0,                  // todo_flags_start
    0                   // todo_flags_finish
};


/*!Add type information used in a statement to json object obj
 *
 * @param file       file descriptor for debuging
 * @param sobj       json object where information is added to
 * @param prefix     prefix for type of level in Gimple description
 * @param node       (sub) tree node we are investigating
 * @param indent     indent depends on level, used for debug print (intention)
    *
 * */
void dump_node(FILE *file, json_object *obj, int item, tree node,
	       int indent)
{
	enum tree_code_class tclass;
	int len;
	int i;
	expanded_location xloc;
	enum tree_code code;
	const char *name;
    char *fname;
	if (node == 0)
		return;

	code = TREE_CODE(node);
	tclass = TREE_CODE_CLASS(code);

	/* Don't get too deep in nesting.  If the user wants to see deeper,
	   it is easy to use the address of a lowest-level node
	   as an argument in another call to debug_tree.  */

	if (indent > 24) {
		return;
	}

	if (indent > 8 && (tclass == tcc_type || tclass == tcc_declaration)) {
		return;
	}

	// It is unsafe to look at any other fields of an ERROR_MARK node.
	if (code == ERROR_MARK) {
		return;
	}

	// Indent to the specified column, since this is the long form.
	indent_to(file, indent);

    if (tclass == tcc_type) {
		if (TYPE_NAME(node)) {
			// Get variable name
			if (TREE_CODE(TYPE_NAME(node)) == IDENTIFIER_NODE) {
				name = IDENTIFIER_POINTER(TYPE_NAME(node));
				if (item == I_STRUCT) {
					json_object *jname = json_object_new_string(name);
					if (!in_jarray(obj, name))
						json_object_array_add(obj, jname);
				}

			} else if (TREE_CODE(TYPE_NAME(node)) == TYPE_DECL &&
				   DECL_NAME(TYPE_NAME(node))) {
				name = IDENTIFIER_POINTER(
				    DECL_NAME(TYPE_NAME(node)));
				if (item == I_STRUCT) {
					json_object *jname = json_object_new_string(name);
					if (!in_jarray(obj, name))
						json_object_array_add(obj, jname);
				}
			}
		}
	}

	if (CODE_CONTAINS_STRUCT(code, TS_TYPED)) {
		dump_node(file, obj, item, TREE_TYPE(node), indent + 3);
		if (TREE_TYPE(node))
			indent_to(file, indent + 3);
	}

	// DECL_ nodes have additional attributes.
	switch (TREE_CODE_CLASS(code)) {
	case tcc_declaration:
        if (item == I_LOC_PRE) {
            xloc = expand_location(DECL_SOURCE_LOCATION(node));
            fname = key_from_path(xloc.file, "pre");
            if (!has_skey(data_pre, fname)) {
                obj = json_object_new_array();
            }
            else{
                obj = json_get_key(data_pre, fname);
                if (obj == NULL){
                    fprintf(stderr, "Error\n");
                    json_object_put(obj);
                }
            }

            if (!int_in_jarray(obj, xloc.line)) {
                json_object *j_line;
                j_line = json_object_new_int(xloc.line);
                if (j_line == NULL) {
                    fprintf(stderr, "%s:%d - Could not create json object\n",
                                __FUNCTION__, __LINE__);
                }
                json_object_array_add(obj, j_line);
                json_set_key(data_pre, fname, obj);
            }
            free(fname);
        }
		if (CODE_CONTAINS_STRUCT(code, TS_DECL_COMMON)) {
			dump_node(file, obj, item, DECL_SIZE(node),
				  indent + 4);
			dump_node(file, obj, item, DECL_SIZE_UNIT(node),
				  indent + 4);

			if (code != FUNCTION_DECL || DECL_BUILT_IN(node))
				indent_to(file, indent + 3);

		}
		if (code == FIELD_DECL) {
			dump_node(file, obj, item, DECL_FIELD_OFFSET(node),
				  indent + 4);
			dump_node(file, obj, item,
				  DECL_FIELD_BIT_OFFSET(node), indent + 4);
			if (DECL_BIT_FIELD_TYPE(node))
				dump_node(file, obj, item,
					  DECL_BIT_FIELD_TYPE(node),
					  indent + 4);
		}

		if (CODE_CONTAINS_STRUCT(code, TS_DECL_NON_COMMON))
			dump_node(file, obj, item, DECL_RESULT_FLD(node),
				  indent + 4);

		if (code == PARM_DECL) {
			dump_node(file, obj, item, DECL_ARG_TYPE(node),
				  indent + 4);
		} else if (code == FUNCTION_DECL &&
			   DECL_STRUCT_FUNCTION(node) != 0) {
			dump_node(file, obj, item, DECL_ARGUMENTS(node),
				  indent + 4);
			indent_to(file, indent + 4);
			dump_addr(file, "", DECL_STRUCT_FUNCTION(node));
		}

		if ((code == VAR_DECL || code == PARM_DECL) &&
		    DECL_HAS_VALUE_EXPR_P(node))
			dump_node(file, obj, item,
				  DECL_VALUE_EXPR(node), indent + 4);

		// Print the decl chain only if decl is at second level.
		if (indent == 4)
			dump_node(file, obj, item, TREE_CHAIN(node), indent + 4);
		break;

	case tcc_type:
		dump_node(file, obj, item, TYPE_SIZE(node), indent + 4);
		dump_node(file, obj, item, TYPE_SIZE_UNIT(node),
			  indent + 4);
		indent_to(file, indent + 3);

		dump_node(file, obj, item, TYPE_ATTRIBUTES(node), indent + 4);

		if (code == ENUMERAL_TYPE)
			dump_node(file, obj, item, TYPE_VALUES(node), indent + 4);
		else if (code == ARRAY_TYPE)
			dump_node(file, obj, item, TYPE_DOMAIN(node), indent + 4);
		else if (code == RECORD_TYPE || code == UNION_TYPE ||
			code == QUAL_UNION_TYPE)
			dump_node(file, obj, item, TYPE_FIELDS(node), indent + 4);
		else if (code == FUNCTION_TYPE || code == METHOD_TYPE) {
			dump_node(file, obj, item, TYPE_ARG_TYPES(node),
				  indent + 4);
		} 

		if (TYPE_POINTER_TO(node) || TREE_CHAIN(node))
			indent_to(file, indent + 3);

		break;

	case tcc_expression:
	case tcc_comparison:
	case tcc_unary:
	case tcc_binary:
	case tcc_reference:
	case tcc_statement:
	case tcc_vl_exp:
		if (code == BIND_EXPR) {
			dump_node(file, obj, item, TREE_OPERAND(node, 0), indent + 4);
			dump_node(file, obj, item, TREE_OPERAND(node, 1), indent + 4);
			dump_node(file, obj, item, TREE_OPERAND(node, 2), indent + 4);
			break;
		}
		if (code == CALL_EXPR) {
			call_expr_arg_iterator iter;
			tree arg;
			dump_node(file, obj, item, CALL_EXPR_FN(node), indent + 4);
			dump_node(file, obj, item,
				  CALL_EXPR_STATIC_CHAIN(node), indent + 4);
			i = 0;
			FOR_EACH_CALL_EXPR_ARG(arg, iter, node)
			{
				dump_node(file, obj, item, arg, indent + 4);
			}
		} else {
			len = TREE_OPERAND_LENGTH(node);

			for (i = 0; i < len; i++) {
				dump_node(file, obj, item, TREE_OPERAND(node, i), indent + 4);
			}
		}
		if (CODE_CONTAINS_STRUCT(code, TS_COMMON))
			dump_node(file, obj, item, TREE_CHAIN(node), indent + 4);
		break;

	case tcc_constant:
	case tcc_exceptional:
		switch (code) {
		case INTEGER_CST:
			break;

		case REAL_CST:  
            break;

		case FIXED_CST:
		    break;

		case VECTOR_CST: {
			unsigned i;
			for (i = 0; i < VECTOR_CST_NELTS(node); ++i) {
				dump_node(file, obj, item, VECTOR_CST_ELT(node, i), indent + 4);
			}
		} break;

		case COMPLEX_CST:
			dump_node(file, obj, item, TREE_REALPART(node), indent + 4);
			dump_node(file, obj, item, TREE_IMAGPART(node), indent + 4);
			break;

		case STRING_CST:  
            break;


		case IDENTIFIER_NODE:
			break;

		case TREE_LIST:
			dump_node(file, obj, item, TREE_PURPOSE(node), indent + 4);
			dump_node(file, obj, item, TREE_VALUE(node), indent + 4);
			dump_node(file, obj, item, TREE_CHAIN(node), indent + 4);
			break;

		case TREE_VEC:
			len = TREE_VEC_LENGTH(node);
			for (i = 0; i < len; i++)
				if (TREE_VEC_ELT(node, i)) {
					dump_node(file, obj, item, TREE_VEC_ELT(node, i), indent + 4);
				}
			break;

		case CONSTRUCTOR: {
			unsigned HOST_WIDE_INT cnt;
			tree index, value;
			len = vec_safe_length(CONSTRUCTOR_ELTS(node));
			FOR_EACH_CONSTRUCTOR_ELT(CONSTRUCTOR_ELTS(node), cnt,
						 index, value)
			{
				dump_node(file, obj, item, index, indent + 4);
				dump_node(file, obj, item, value, indent + 4);
			}
		} break;

		case STATEMENT_LIST:
			{
                tree_stmt_iterator i;
				for (i = tsi_start(node); !tsi_end_p(i);
				     tsi_next(&i)) {
					/* Not printing the addresses of the
					(not-a-tree)
					'struct tree_stmt_list_node's.  */
					dump_node(file, obj, item, tsi_stmt(i), indent + 4);
				}
			}
			break;

		case BLOCK:
			dump_node(file, obj, item, BLOCK_VARS(node), indent + 4);
			dump_node(file, obj, item, BLOCK_SUPERCONTEXT(node), indent + 4);
			dump_node(file, obj, item, BLOCK_SUBBLOCKS(node), indent + 4);
			dump_node(file, obj, item, BLOCK_CHAIN(node), indent + 4);
			dump_node(file, obj, item, BLOCK_ABSTRACT_ORIGIN(node), indent + 4);
			break;

		case SSA_NAME:
			indent_to(file, indent + 4);

			if (SSA_NAME_PTR_INFO(node)) 
				indent_to(file, indent + 3);
			
			break;

		case OMP_CLAUSE:
		    break;

		case OPTIMIZATION_NODE:
			cl_optimization_print(file, indent + 4,
					      TREE_OPTIMIZATION(node));
			break;

		case TARGET_OPTION_NODE:
			cl_target_option_print(file, indent + 4,
					       TREE_TARGET_OPTION(node));
			break;
		case IMPORTED_DECL:
			break;

		case TREE_BINFO:
			break;

		default:
			if (EXCEPTIONAL_CLASS_P(node))
				// MK lang_hooks.print_xnode (file, node,
				// indent);
				break;
		}

		break;
	}
    if (EXPR_HAS_LOCATION (node) && item == I_LOC_PRE) {
        expanded_location xloc = expand_location (EXPR_LOCATION (node));
        expanded_location xloc_f;
        expanded_location xloc_s;
        indent_to (file, indent+4);
        int j;
        json_object *j_line;
        if (strcmp("<built-in>", xloc.file) == 0)
            return;

        json_object *obj = json_object_new_array();

        fname = key_from_path(xloc.file, "pre");
        if (!has_skey(data_pre, fname)) {
            obj = json_object_new_array();
        }
        else{
            obj = json_get_key(data_pre, fname);
            if (obj == NULL){
                fprintf(stderr, "Error\n");
                json_object_put(obj);
            }
        }
        //if (strcmp("kernel/rcu/tree.c", xloc.file) == 0)
        //    debug_tree(node);

        json_set_key(data_pre, fname, obj);
        /* Print the range, if any */
        source_range r = EXPR_LOCATION_RANGE (node);
        if (!r.m_finish) {
            xloc = expand_location (r.m_start);
            if (!int_in_jarray(obj, xloc.line)) {
                j_line = json_object_new_int(xloc.line);
                if (j_line == NULL) {
                    fprintf(stderr, "%s:%d - Could not create json object\n",
                                __FUNCTION__, __LINE__);
                }
                json_object_array_add(obj, j_line);
            }
        }
        else {
            xloc_f = expand_location (r.m_finish);
            xloc_s = expand_location (r.m_start);
            for(j = xloc_s.line; j <= xloc_f.line; j++) {
                if (!int_in_jarray(obj, j)) {
                    j_line = json_object_new_int(j);
                    if (j_line == NULL) {
                        fprintf(stderr, "%s:%d - Could not create json object\n",
                                __FUNCTION__, __LINE__);
                    }
                    // XXX
                    json_object_array_add(obj, j_line);
                }
            }
        }

        json_set_key(data_pre, fname, obj);
        free(fname);
    }
}


/*!Class for PLUGIN_PASS_MANAGER_SETUP pass.
 */
struct get_stmt_pass : gimple_opt_pass {
	get_stmt_pass(gcc::context *ctx)
	    : gimple_opt_pass(get_stmt_pass_data, ctx)
	{
	}

    /*!Add type information used in a statement to json object obj
     * This function is called by the GCC during the PASS
     * PLUGIN_PASS_MANAGER_SETUP.
     *
     * @param fun   pointer to current process function
     *
     * */
	virtual unsigned int execute(function *fun) override
	{
		int start, end;

		expanded_location xloc;
		tree arg;
		int fun_decl_start;
		int fun_decl_end;
        char *fname;

		// fun is the current function being called
		gimple_seq gimple_body = fun->gimple_body;
		cur_func = get_name(fun->decl);

		cur_file = LOCATION_FILE(fun->function_end_locus);
        //fprintf(stderr, "%d", LOCATION_LINE()); //XXX
        fname = key_from_path(cur_file, "dl");
        if (strcmp(cur_func, "inet_lookup_established") == 0) {
            xloc = expand_location(DECL_SOURCE_LOCATION(fun->decl));
	        fprintf(stderr, "--> %d", xloc.line);	
        }
        
        xloc = expand_location(DECL_SOURCE_LOCATION(fun->decl));
        start = xloc.line;
        if (DECL_ARGUMENTS(fun->decl)) {
            tree args = DECL_ARGUMENTS(fun->decl);
            fname = key_from_path(xloc.file, "dl");
            fun_decl_start = xloc.line;
            fun_decl_end = xloc.line;

            for (arg = args; arg; arg = TREE_CHAIN(arg)) {
                xloc = expand_location(DECL_SOURCE_LOCATION(arg));
                fun_decl_end = xloc.line;
            }
            dump_data(data_dlen, fname, cur_func, fun_decl_start,
                  fun_decl_end);
        } else {
            xloc = expand_location(DECL_SOURCE_LOCATION(fun->decl));
            fname = key_from_path(xloc.file, "dl");
            dump_data(data_dlen, fname, cur_func, xloc.line,
                  xloc.line);
        }

        free(fname);

		//start = LOCATION_LINE(fun->function_start_locus);
		end = LOCATION_LINE(fun->function_end_locus);
        fname = key_from_path(cur_file, "fl");
		//dump_data(data_flen, fname, cur_func, start, end);
		dump_data(data_flen, fname, cur_func, start, end);
        free(fname);
		struct walk_stmt_info walk_stmt_info;
		memset(&walk_stmt_info, 0, sizeof(walk_stmt_info));

		walk_gimple_seq(gimple_body, callback_stmt, callback_op,
				&walk_stmt_info);

		return 0;
	}

	virtual get_stmt_pass *clone() override
	{
		// We do not clone ourselves
		return this;
	}
      private:
    /*!Callback function for walk_gimple_seq. This function walks all the
     * statements in the sequence SEQ calling walk_gimple_stmt on each one.
     * Iterate over operands and get used declarations by calling dump_node.
     *
     *
     * @param gsi               statement handled
     * @param handled_all_ops   callback function called after each operand
     * @param wi                wi is as in walk_gimple_stmt
     *
     * */
	static tree callback_stmt(gimple_stmt_iterator *gsi,
				  bool *handled_all_ops,  struct walk_stmt_info *wi)
	{
		gimple *g = gsi_stmt(*gsi);
		tree op;
		location_t l = gimple_location(g);
		const char *name;
		char *fname = NULL;
		int line, ret;
		size_t i, j, len;
		json_object *decl_file;
        json_object *stmt_file;
        json_object *ustruct_file;
        const char *cfname;
		line = LOCATION_LINE(l);
        cfname = LOCATION_FILE(l);

        if(cfname == NULL)
            return NULL;

        fname = key_from_path(cfname, "stmt");
        // print_gimple_expr (stderr, g, 0, TDF_VOPS|TDF_MEMSYMS);

        if (!has_skey(data_stmt, fname)){
            stmt_file = json_object_new_array();
        }
        else{
            stmt_file = json_get_key(data_stmt, fname);
            if (stmt_file == NULL){
                fprintf(stderr, "Error\n");
				json_object_put(stmt_file);
            }
        }

		// Add executed line to stmt list
		if (!int_in_jarray(stmt_file, line)) {
			json_object *jline = json_object_new_int(line);
			json_object_array_add(stmt_file, jline);
            ret = json_set_key(data_stmt, fname, stmt_file);
            if (ret != true)
                fprintf(stderr, "error dict\n");
		}
        free(fname);
        //print_gimple_expr (stderr, g, 0, TDF_VOPS|TDF_MEMSYMS);
		for (i = 0; i < gimple_num_ops(g); ++i) {
			if ((op = gimple_op(g, i)) == NULL)
                continue;

			if (TREE_CODE(op) == VAR_DECL) {
				if (DECL_NAME(op)) {
					name = IDENTIFIER_POINTER(DECL_NAME(op));
                    line = DECL_SOURCE_LINE(op);
                    //fprintf(stderr, "LINE:%d\n", line);
                    fname = key_from_path(cfname, "decl");

					json_object *sobj = json_object_new_array();
					dump_node(log_fd, sobj, I_STRUCT, op, 0);

					if (json_object_array_length(sobj) == 0) {
						json_object_put(sobj);
                        free(fname);
						continue;
					}
                    /* check if there is current file */
                    if (!has_skey(data_decl, fname))
                        decl_file = json_object_new_object();
                    else {
                        decl_file = json_get_key(data_decl, fname);
                        if (decl_file == NULL){
                            fprintf(stderr, "Error\n");
							json_object_put(sobj);
                        }
                    }

					char *key;
					ret = asprintf(&key, "%d", line);
					if (ret == -1) {
						fprintf(stderr,
						    "[%s:%d] Could not convert the line\n",
						    __FUNCTION__,__LINE__);
						json_object_put(sobj);
                        free(fname);
						continue;
                    }
					if (!has_skey(decl_file, key))
						json_object_object_add(decl_file, key, sobj);
                    else {
						json_object *pobj;
						json_object_object_get_ex(decl_file, key, &pobj);

						if (!has_skey(pobj, name)) {
							json_object *jname = json_object_new_string(name);
							json_object_array_add(pobj, jname);
						}
					}
                    free(key);
                    json_set_key(data_decl, fname, decl_file);
                    free(fname);
				}
            }

            /* Get used struct in statement */
            if (TREE_CODE(op) == COMPONENT_REF) {
				json_object *sobj = json_object_new_array();
				dump_node(log_fd, sobj, I_STRUCT, op, 0);
				if (json_object_array_length(sobj) ==0) {
					continue;
				}
                fname = key_from_path(cfname, "us");
                /* check if there is current file */
                if (!has_skey(data_ustruct, fname))
                    ustruct_file = json_object_new_object();
                else {
                    ustruct_file = json_get_key(data_ustruct, fname);
                    if (ustruct_file == NULL){
                        fprintf(stderr, "Error get key in data_ustruct\n");
						json_object_put(sobj);
                    }
                }
				char *key;
				ret = asprintf(&key, "%d", line);
				if (ret == -1) {
					fprintf(stderr,
						"[%s:%d] Could not convert the line\n",
						__FUNCTION__, __LINE__);
					continue;
				}
				if (!has_skey(ustruct_file, key)) {
					json_object_object_add(ustruct_file, key, sobj);
				}
                else {
					char *_line;
					json_object *tok;
					ret = asprintf(&_line, "%d", line);

					if (ret == -1) {
						fprintf(stderr,
							"[%s:%d] Could not convert the line\n",
							__FUNCTION__, __LINE__);
						continue;
					}
					ret = json_object_object_get_ex(ustruct_file, key, &tok);
					if (ret == 1) {
						len = json_object_array_length(sobj);
						for (j = 0; j < len; j++) {
							json_object *it;
							it = json_object_array_get_idx(sobj, j);

							const char *it_str = json_object_get_string(it);
							if (in_jarray(tok, it_str)) {
								continue;
							}
							json_object *jit = json_object_new_string(it_str);
							json_object_array_add(tok, jit);
						}
					}
				}
				free(key);
                json_set_key(data_ustruct, fname, ustruct_file);
                //free(fname);
			}
		}
		return NULL;
	}
    /*! Callback function after each operand, if this does function does
     * not return NULL the other operand won't be scanned so, return NULL
     *
     * @param t         tree
     * @param *         ??
     * @param data      wi is as in walk_gimple_stmt
     *
     * @return          if this does function does, not return NULL the other
     *                  operand won't be scanned so, return NULL
     *
     * */
	static tree callback_op(tree *t, int *, void *data) {
        return NULL;
    }
};
}

/*! Get structure information pass. Output will be stored with appendix
 * file_name.st_def with structure name and corrsponding start/end line
 * information.
 *
 * @param user_data        plugin-specific data provided by the plug-in
 * @param event_data       event-specific data provided by GCC
 *
 * */
static void get_structs(void *event_data, void *user_data)
{
	(void)user_data;
	tree type = (tree)event_data;
	const char *name;
	char *fname;
	tree field;
	// We only care about structs, not any other type definition.
	if ((TREE_CODE(type) == RECORD_TYPE) ||
	    (DECL_ARTIFICIAL(type) || DECL_THIS_EXTERN(type))) {
        int start = -1;
        int end = 0;
        tree _field;

		// Struct name?
		tree name_tree = TYPE_NAME(type);

		// Ignore unnamed structs.
		if (!name_tree)
			return;

        else {
            if (TREE_CODE(name_tree) == IDENTIFIER_NODE)
				name = IDENTIFIER_POINTER(name_tree);
			else if (TREE_CODE(name_tree) == TYPE_DECL &&
				 DECL_NAME(name_tree))
				name = IDENTIFIER_POINTER(DECL_NAME(name_tree));
			else
                return;
			// If the type is not complete, we can't do anything.
			if (!COMPLETE_TYPE_P(type))
				return;
            for (field = TYPE_FIELDS(type); field; field = TREE_CHAIN(field)) {
                tree name_tree = TYPE_NAME(type);
                // Ignore unnamed structs.
                if (!name_tree)
                    return;
                else {
                    if (TREE_CODE(name_tree) == IDENTIFIER_NODE) {
                        if (DECL_NAME(field) != NULL) {
                            if (start == -1) {
                                name = IDENTIFIER_POINTER(name_tree);
                                start = DECL_SOURCE_LINE(field);
                                _field = field;
                            }
                            end = DECL_SOURCE_LINE(field);
                        }
                    } else if (TREE_CODE(name_tree) == TYPE_DECL &&
                               DECL_NAME(name_tree)) {
                        if (start == -1) {
                                name = IDENTIFIER_POINTER(DECL_NAME(name_tree));
                                start = DECL_SOURCE_LINE(field);
                                _field = field;
                        }
                        end = DECL_SOURCE_LINE(field);
                    } else {
                        name = "unknown struct name";
                        continue;
                    }
                }
            }
            if (start != -1) {
                int ret;
                ret = strncmp("/usr", DECL_SOURCE_FILE(_field), strlen("/usr"));
                if (ret == 0)
                    return;

                fname = key_from_path(DECL_SOURCE_FILE(_field), "st_def");
                dump_data(data_struct, fname, name, start, end);
                free(fname);
            }
		}
	}
}

 /*!Get variable declaration. Called at the end of each declaration
 *
 * @param user_data        plugin-specific data provided by the plug-in
 * @param event_data       event-specific data provided by GCC
 *
 * */
static void get_decl(void *event_data, void *user_data)
{
    char *fname;
    tree node = (tree)event_data;
	static json_object *stmt_file;
    int line;



    if (TREE_CODE(node) != PARM_DECL && !DECL_EXTERNAL(node)) {
        if (DECL_NAME (node)) {

            /* consider only project files no compiler includes
             * -> It is just a fix, I do not know the proper way atm */
            int ret = strncmp("/usr", DECL_SOURCE_FILE(node), strlen("/usr"));
            if (ret == 0)
                return;
            line = DECL_SOURCE_LINE(node);
            fname = key_from_path(DECL_SOURCE_FILE(node),"stmt");
            /* check if there is current file */
            if (!has_skey(data_stmt, fname)){
                stmt_file = json_object_new_array();
            }
            else{
                stmt_file = json_get_key(data_stmt, fname);
                if (stmt_file == NULL){
                    fprintf(stderr, "Error\n");
                    json_object_put(stmt_file);
                }
            }

            // Add executed line to stmt list
            if (!int_in_jarray(stmt_file, line)) {
                json_object *jline = json_object_new_int(line);
                json_object_array_add(stmt_file, jline);
            }
            json_set_key(data_stmt, fname, stmt_file);
            free(fname);
        }
    }
    else
        line = DECL_SOURCE_LINE(node);
}



static json_object * load_data(const char *suffix)
{
    FILE *fp;
    char *fname;
    int bufsize ,ret;
    char *contents;
    json_object *obj = NULL;

	ret = asprintf(&fname, "%s/data_%s.json", out_path, suffix);
    if (ret == -1) {
        fprintf(stderr,
            "[%s:%d] Could not asprintf\n", __FUNCTION__, __LINE__);
        return 0;
    }
    if (f_exists(fname)) {
        fp = fopen(fname, "r");
        if (fp == NULL) {
            fprintf(stderr, "Error read data from json: %s\n", fname);
            return NULL;
        }

        if (fseek(fp, 0L, SEEK_END) != 0) {
            perror("Could not seek the end of the file\n");
            goto error;
        }

        // Get size of the file.
        bufsize = ftell(fp);
        if (bufsize == -1) {
            perror("ftell failed\n");
            goto ftell_error;
        }

        contents = (char *)xcalloc(sizeof(char), bufsize + 1);
        if (fseek(fp, 0L, SEEK_SET) != 0) {
            perror("Seek failed\n");
            goto fseek_error;
        }

        if (fread(contents, sizeof(char), bufsize, fp) == 0) {
            fprintf(stderr, "Error reading file: %s", fname);
            goto fread_error;
        }

        fclose(fp);
        obj = json_tokener_parse(contents);
        free(contents);
    }
    else {
        /* init global json data variables first time no files */
        obj = json_object_new_object();
    }
    free(fname);
    return obj;

fread_error:
fseek_error:
        free(fname);
        free(contents);
ftell_error:
error:
        fclose(fp);
        return obj;
}

static void init_data()
{
    data_decl = load_data("decl");
    data_stmt = load_data("stmt");
    data_struct = load_data("struct");
    data_dlen = load_data("dlen");
    data_flen = load_data("flen");
    data_pre = load_data("pre");
    data_ustruct = load_data("ustruct");
}

static int write_data(json_object *obj, const char *suffix)
{
    FILE *fd;
    char *path;
    int ret;
    char *fname;

    if(obj == NULL)
        return 0;

    asprintf(&fname, "%s/data_%s.json", out_path, suffix);
    fd = fopen(fname, "w");
    if (fd == NULL) {
        perror("fopen");
        return 1;
    }
    fprintf(fd, "%s", json_object_to_json_string(obj));
    fclose(fd);
    return 0;

    json_object *mtok;
    json_object_object_foreach(obj, skey, sval)
    {
        // Get if available object form main object list
        ret = json_object_object_get_ex(obj, skey, &mtok);
        if (ret == 1) {
            path = get_path(skey);
            if (!d_exists(path)) {
                ret = pit_mkdir(path);
            }
            free(path);

            if (ret == -1)
                return -1;

            if (f_exists(skey)) {
                fprintf(stderr, "%s:%d The file: %s needs merge\n",
                            __FUNCTION__, __LINE__, skey);
            }


	        fd = fopen(skey, "w");
            if (fd == NULL) {
		        perror("fopen");
		        return 1;
	        }
            fprintf(fd, "%s", json_object_to_json_string(mtok));
            fclose(fd);
        }
    }
    return 0;
}


/*!Get global variables pass. Called at the end of compile unit compilation.
 *
 * @param user_data        plugin-specific data provided by the plug-in
 * @param event_data       event-specific data provided by GCC
 *
 * */
static void finish(void *event_data, void *user_data)
{
	const char *name, *type;
	const char *fname;
	struct varpool_node *node;
	int line;

    //fprintf(stderr, "DECL: %s\n", json_object_to_json_string(data_decl));
    write_data(data_stmt, "stmt");
    write_data(data_decl, "decl");
    write_data(data_struct, "struct");
    write_data(data_dlen, "dlen");
    write_data(data_flen, "flen");
    write_data(data_pre, "pre");
    write_data(data_ustruct, "ustruct");
    
    return;
    /* save global code needs to be adapted */
	FOR_EACH_VARIABLE(node)
	{
		tree var = NODE_DECL(node);
		name = IDENTIFIER_POINTER(DECL_NAME(var));
		line = DECL_SOURCE_LINE(var);
		fname = DECL_SOURCE_FILE(var);
		type = get_tree_code_name(TREE_CODE(TREE_TYPE(var)));
		save_global(fname, name, type, TREE_PUBLIC(var), line);
	}
}


/*!GCC Plugin pass PLUGIN_PRE_GENERICIZE, basicaly after the c-code 
 * has been parsed
 *
 * @param event_data
 * @param user_data
 *
 * */
void pre_genericize(void *event_data, void *user_data) {
    
    tree fndecl = (tree) event_data, decl;

    if (DECL_ARTIFICIAL (fndecl))
        return;

    decl = DECL_SAVED_TREE (fndecl);
    json_object *obj = json_object_new_array();
    dump_node(log_fd, obj, I_LOC_PRE, decl, 0);

	return;
}


/*!GCC Plugin init routine
 *
 * @param plugin_info plugin arguments
 * @param version     plugin version
 *
 * @return If initialization fails, plugin_init returns a non-zero value.
 * otherwise, it should return 0.
 * */
int plugin_init(struct plugin_name_args *plugin_info,
		struct plugin_gcc_version *version)
{
	int i, ret;
	struct register_pass_info pass_info;

	/* We check the current gcc loading this plugin against the gcc we used
	   to
	   created this plugin */
	if (!plugin_default_version_check(version, &gcc_version)) {
		fprintf(stderr, "This GCC plugin is for version %d. %d",
			GCCPLUGIN_VERSION_MAJOR, GCCPLUGIN_VERSION_MINOR);

		return 1;
	}

	for (i = 0; i < plugin_info->argc; ++i) {
		if (strcmp(plugin_info->argv[i].key, "log") == 0) {
			asprintf(&out_path, "%s", plugin_info->argv[i].value);
		}
		if (strcmp(plugin_info->argv[i].key, "base") == 0) {
			asprintf(&base_path, "%s", plugin_info->argv[i].value);
		}
	}

	if (!d_exists(out_path)) {
		ret = pit_mkdir(out_path);
	}

	if (ret == -1)
		return -1;



	// Register the phase right after omplower
	log_fd = fopen("/tmp/log.txt", "w");
	if (log_fd == NULL) {
		perror("fopen");
		return 1;
	}

	/* Note that after the cfg is built, fun->gimple_body is not accessible
	   anymore so we run this pass just before the cfg one. */
	pass_info.pass = new get_stmt_pass(g);
	pass_info.reference_pass_name = "cfg";
	pass_info.ref_pass_instance_number = 1;
	pass_info.pos_op = PASS_POS_INSERT_BEFORE;
    
	register_callback(plugin_info->base_name, PLUGIN_INFO, NULL,
			  &pic_gcc_plugin_info);
	register_callback(plugin_info->base_name, PLUGIN_PASS_MANAGER_SETUP,
			  NULL, &pass_info);
	register_callback(plugin_info->base_name, PLUGIN_FINISH_TYPE,
			  get_structs, NULL);
	register_callback(plugin_info->base_name, PLUGIN_FINISH, finish,
			  NULL);
    register_callback(plugin_info->base_name, PLUGIN_FINISH_DECL, get_decl,
              NULL);
    register_callback(plugin_info->base_name, PLUGIN_START_UNIT,
                    (plugin_callback_func) init_data, NULL);
    

    register_callback(plugin_info->base_name, PLUGIN_PRE_GENERICIZE,
                    (plugin_callback_func) pre_genericize, NULL);
	return 0;
}
