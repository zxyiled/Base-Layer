import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _ensure_headless_tk():

    try:
        import tkinter  # noqa: F401
        return
    except ImportError:
        pass

    tk = types.ModuleType("tkinter")
    tk.END = "end"
    tk.BOTH = "both"
    tk.W = "w"
    tk.TEXT = "text"
    tk.NORMAL = "normal"
    tk.DISABLED = "disabled"
    tk.X = "x"
    tk.NONE = "none"
    tk.Tk = lambda *a, **k: None
    tk.Toplevel = lambda *a, **k: None
    tk.Text = lambda *a, **k: None
    tk.Frame = lambda *a, **k: None
    tk.Entry = lambda *a, **k: None
    tk.Button = lambda *a, **k: None
    tk.Menu = lambda *a, **k: None
    sys.modules["tkinter"] = tk

    ttk = types.ModuleType("tkinter.ttk")
    ttk.Frame = type("Frame", (), {})
    ttk.Label = type("Label", (), {})
    ttk.LabelFrame = type("LabelFrame", (), {})
    ttk.Button = type("Button", (), {})
    ttk.Entry = type("Entry", (), {})
    sys.modules["tkinter.ttk"] = ttk

    mb = types.ModuleType("tkinter.messagebox")
    mb.showinfo = lambda *a, **k: None
    mb.showerror = lambda *a, **k: None
    sys.modules["tkinter.messagebox"] = mb


_ensure_headless_tk()

from matrix_calculator import Matrix, parse_matrix_text, register_history  # noqa: E402


class TestMatrixCreation(unittest.TestCase):

    def test_creation(self):
        m = Matrix([[1, 2], [3, 4]])
        self.assertEqual(m.rows, 2)
        self.assertEqual(m.columns, 2)
        self.assertEqual(m.data, [[1, 2], [3, 4]])

    def test_creation_rectangle(self):
        m = Matrix([[1, 2, 3], [4, 5, 6]])
        self.assertEqual(m.rows, 2)
        self.assertEqual(m.columns, 3)

    def test_empty_matrix_raises(self):
        with self.assertRaises(ValueError):
            Matrix([])
        with self.assertRaises(ValueError):
            Matrix([[]])

    def test_irregular_rows_raises(self):
        with self.assertRaises(ValueError):
            Matrix([[1, 2], [3]])

    def test_copies_input_data(self):
        original = [[1, 2], [3, 4]]
        m = Matrix(original)
        original[0][0] = 99
        self.assertEqual(m.data[0][0], 1)

    def test_max_dimension_limit_accepted(self):
        data = [[0.0] * Matrix.MAX_DIMENSION for _ in range(Matrix.MAX_DIMENSION)]
        m = Matrix(data)
        self.assertEqual(m.rows, Matrix.MAX_DIMENSION)
        self.assertEqual(m.columns, Matrix.MAX_DIMENSION)

    def test_rows_over_limit_raises(self):
        with self.assertRaises(ValueError):
            Matrix([[0.0] * 3 for _ in range(Matrix.MAX_DIMENSION + 1)])

    def test_columns_over_limit_raises(self):
        with self.assertRaises(ValueError):
            Matrix([[0.0] * (Matrix.MAX_DIMENSION + 1) for _ in range(3)])

    def test_both_dimensions_over_limit_raises(self):
        with self.assertRaises(ValueError):
            Matrix([[0.0] * (Matrix.MAX_DIMENSION + 1) for _ in range(Matrix.MAX_DIMENSION + 1)])


class TestStr(unittest.TestCase):

    def test_str_contains_values(self):
        s = str(Matrix([[1, 2], [3, 4]]))
        self.assertIn("1", s)
        self.assertIn("2", s)
        self.assertIn("3", s)
        self.assertIn("4", s)

    def test_str_has_line_per_row(self):
        s = str(Matrix([[1, 2], [3, 4]]))
        self.assertEqual(len(s.splitlines()), 2)


class TestSizeValidation(unittest.TestCase):

    def test_matching_size_ok(self):
        a = Matrix([[1, 2], [3, 4]])
        b = Matrix([[5, 6], [7, 8]])
        a._validate_size(b)  # no debe lanzar

    def test_mismatched_size_raises(self):
        a = Matrix([[1, 2], [3, 4]])
        b = Matrix([[1, 2, 3]])
        with self.assertRaises(ValueError):
            a._validate_size(b)


class TestIsSquare(unittest.TestCase):

    def test_square(self):
        self.assertTrue(Matrix([[1, 2], [3, 4]]).is_square())

    def test_non_square(self):
        self.assertFalse(Matrix([[1, 2, 3]]).is_square())


class TestAdd(unittest.TestCase):

    def test_add_2x2(self):
        result = Matrix([[1, 2], [3, 4]]).add(Matrix([[5, 6], [7, 8]]))
        self.assertEqual(result.data, [[6, 8], [10, 12]])

    def test_add_float(self):
        result = Matrix([[1.5, 2.5]]).add(Matrix([[0.5, 0.5]]))
        self.assertEqual(result.data, [[2.0, 3.0]])

    def test_add_incompatible_raises(self):
        with self.assertRaises(ValueError):
            Matrix([[1, 2], [3, 4]]).add(Matrix([[1, 2, 3]]))


class TestSubtract(unittest.TestCase):

    def test_subtract_2x2(self):
        result = Matrix([[5, 6], [7, 8]]).subtract(Matrix([[1, 2], [3, 4]]))
        self.assertEqual(result.data, [[4, 4], [4, 4]])

    def test_subtract_negative_results(self):
        result = Matrix([[1, 2], [3, 4]]).subtract(Matrix([[5, 6], [7, 8]]))
        self.assertEqual(result.data, [[-4, -4], [-4, -4]])

    def test_subtract_incompatible_raises(self):
        with self.assertRaises(ValueError):
            Matrix([[1, 2], [3, 4]]).subtract(Matrix([[1, 2, 3]]))


class TestMultiply(unittest.TestCase):

    def test_multiply_2x2(self):
        result = Matrix([[1, 2], [3, 4]]).multiply(Matrix([[5, 6], [7, 8]]))
        self.assertEqual(result.data, [[19, 22], [43, 50]])

    def test_multiply_rectangular(self):
        a = Matrix([[1, 2, 3], [4, 5, 6]])
        b = Matrix([[7, 8], [9, 10], [11, 12]])
        result = a.multiply(b)
        self.assertEqual(result.rows, 2)
        self.assertEqual(result.columns, 2)
        self.assertEqual(result.data, [[58, 64], [139, 154]])

    def test_multiply_by_identity(self):
        a = Matrix([[2, 3], [5, 7]])
        identity = Matrix([[1, 0], [0, 1]])
        result = a.multiply(identity)
        self.assertEqual(result.data, a.data)

    def test_multiply_incompatible_raises(self):
        with self.assertRaises(ValueError):
            Matrix([[1, 2]]).multiply(Matrix([[1, 2]]))


class TestScalarMultiply(unittest.TestCase):

    def test_scalar_multiply(self):
        result = Matrix([[1, 2], [3, 4]]).scalar_multiply(3)
        self.assertEqual(result.data, [[3, 6], [9, 12]])

    def test_scalar_multiply_negative(self):
        result = Matrix([[1, 2]]).scalar_multiply(-2)
        self.assertEqual(result.data, [[-2, -4]])

    def test_scalar_multiply_zero(self):
        result = Matrix([[1, 2]]).scalar_multiply(0)
        self.assertEqual(result.data, [[0.0, 0.0]])


class TestTranspose(unittest.TestCase):

    def test_transpose_square(self):
        result = Matrix([[1, 2], [3, 4]]).transpose()
        self.assertEqual(result.data, [[1, 3], [2, 4]])

    def test_transpose_rectangular(self):
        result = Matrix([[1, 2, 3], [4, 5, 6]]).transpose()
        self.assertEqual(result.data, [[1, 4], [2, 5], [3, 6]])

    def test_transpose_twice_returns_original(self):
        m = Matrix([[1, 2, 3], [4, 5, 6]])
        self.assertEqual(m.transpose().transpose().data, m.data)


class TestTrace(unittest.TestCase):

    def test_trace_2x2(self):
        self.assertEqual(Matrix([[1, 2], [3, 4]]).trace(), 5.0)

    def test_trace_3x3(self):
        m = Matrix([[6, 1, 1], [4, -2, 5], [2, 8, 7]])
        self.assertAlmostEqual(m.trace(), 11.0)

    def test_trace_1x1(self):
        self.assertEqual(Matrix([[42]]).trace(), 42.0)

    def test_trace_non_square_raises(self):
        with self.assertRaises(ValueError):
            Matrix([[1, 2, 3]]).trace()


class TestDeterminant(unittest.TestCase):

    def test_determinant_1x1(self):
        self.assertAlmostEqual(Matrix([[7]]).determinant(), 7.0)

    def test_determinant_2x2(self):
        self.assertAlmostEqual(Matrix([[1, 2], [3, 4]]).determinant(), -2.0)

    def test_determinant_3x3(self):
        m = Matrix([[6, 1, 1], [4, -2, 5], [2, 8, 7]])
        self.assertAlmostEqual(m.determinant(), -306.0)

    def test_determinant_identity(self):
        m = Matrix([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        self.assertAlmostEqual(m.determinant(), 1.0)

    def test_determinant_singular(self):
        self.assertAlmostEqual(Matrix([[1, 2], [2, 4]]).determinant(), 0.0)

    def test_determinant_row_swap_negative(self):
        m = Matrix([[0, 1], [2, 3]])
        self.assertAlmostEqual(m.determinant(), -2.0)

    def test_determinant_diagonal(self):
        m = Matrix([[2, 0, 0], [0, 3, 0], [0, 0, 4]])
        self.assertAlmostEqual(m.determinant(), 24.0)

    def test_determinant_non_square_raises(self):
        with self.assertRaises(ValueError):
            Matrix([[1, 2, 3]]).determinant()

    def test_determinant_max_size_completes(self):
        identity = Matrix([
            [1.0 if i == j else 0.0 for j in range(Matrix.MAX_DIMENSION)]
            for i in range(Matrix.MAX_DIMENSION)
        ])
        self.assertAlmostEqual(identity.determinant(), 1.0, places=8)

    def test_determinant_matches_reference(self):
        def det_cofactor(m):
            n = len(m)
            if n == 1:
                return m[0][0]
            if n == 2:
                return m[0][0] * m[1][1] - m[0][1] * m[1][0]
            return sum(
                m[0][j] * ((-1) ** j) * det_cofactor(
                    [[m[i][k] for k in range(n) if k != j] for i in range(1, n)]
                )
                for j in range(n)
            )

        cases = [
            [[1, 2, 3], [4, 5, 6], [7, 8, 10]],
            [[0, 2, 1], [3, 0, 1], [1, 1, 1]],
            [[3, 5], [2, 7]],
            [[2, 0, 0], [0, 0, 0], [0, 0, 5]],
            [[1, 0, 0], [0, 2, 0], [0, 0, 3]],
            [[5]],
        ]
        for case in cases:
            self.assertAlmostEqual(
                Matrix(case).determinant(), det_cofactor(case), places=8
            )


class TestAdjoint(unittest.TestCase):

    def test_adjoint_2x2(self):
        result = Matrix([[1, 2], [3, 4]]).adjoint()
        self.assertEqual(result.data, [[4.0, -2.0], [-3.0, 1.0]])

    def test_adjoint_identity(self):
        result = Matrix([[1, 0], [0, 1]]).adjoint()
        self.assertEqual(result.data, [[1.0, 0.0], [0.0, 1.0]])

    def test_adjoint_1x1(self):
        result = Matrix([[5]]).adjoint()
        self.assertEqual(result.data, [[1.0]])

    def test_adjoint_a_times_adjoint_equals_det_identity(self):
        m = Matrix([[6, 1, 1], [4, -2, 5], [2, 8, 7]])
        det = m.determinant()
        product = m.multiply(m.adjoint())
        for i in range(3):
            for j in range(3):
                expected = det if i == j else 0.0
                self.assertAlmostEqual(product.data[i][j], expected, places=8)

    def test_adjoint_singular_matrix(self):
        m = Matrix([[1, 2], [2, 4]])
        adj = m.adjoint()
        self.assertEqual(adj.rows, 2)
        self.assertEqual(adj.columns, 2)

    def test_adjoint_non_square_raises(self):
        with self.assertRaises(ValueError):
            Matrix([[1, 2, 3]]).adjoint()


class TestInverse(unittest.TestCase):

    def test_inverse_2x2(self):
        result = Matrix([[1, 2], [3, 4]]).inverse()
        expected = [[-2.0, 1.0], [1.5, -0.5]]
        for i in range(2):
            for j in range(2):
                self.assertAlmostEqual(result.data[i][j], expected[i][j], places=10)

    def test_inverse_times_matrix_is_identity(self):
        m = Matrix([[4, 7], [2, 6]])
        identity = m.multiply(m.inverse())
        for i in range(2):
            for j in range(2):
                expected = 1.0 if i == j else 0.0
                self.assertAlmostEqual(identity.data[i][j], expected, places=8)

    def test_inverse_of_identity(self):
        m = Matrix([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        result = m.inverse()
        for i in range(3):
            for j in range(3):
                expected = 1.0 if i == j else 0.0
                self.assertAlmostEqual(result.data[i][j], expected, places=8)

    def test_inverse_non_square_raises(self):
        with self.assertRaises(ValueError):
            Matrix([[1, 2, 3]]).inverse()

    def test_inverse_singular_raises(self):
        with self.assertRaises(ValueError):
            Matrix([[1, 2], [2, 4]]).inverse()


class TestRegisterHistory(unittest.TestCase):

    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory(prefix="matrix_test_")
        self._original_cwd = os.getcwd()
        os.chdir(self._temp_dir.name)

    def tearDown(self):
        os.chdir(self._original_cwd)
        self._temp_dir.cleanup()

    def test_history_file_is_created(self):
        register_history("Suma A + B", "1.0000")
        self.assertTrue(os.path.exists("historial.txt"))

    def test_history_appends_entries(self):
        register_history("Resta A - B", "2.0000")
        register_history("Multiplicación A * B", "3.0000")
        with open("historial.txt", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Resta A - B", content)
        self.assertIn("Multiplicación A * B", content)
        self.assertIn("2.0000", content)
        self.assertIn("3.0000", content)
        self.assertEqual(content.count("Resultado:"), 2)


class TestParseMatrixText(unittest.TestCase):

    def test_parse_basic(self):
        m = parse_matrix_text("1 2 3\n4 5 6")
        self.assertEqual(m.data, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(m.rows, 2)
        self.assertEqual(m.columns, 3)

    def test_parse_extra_whitespace(self):
        m = parse_matrix_text("  1   2  \n  3   4  ")
        self.assertEqual(m.data, [[1, 2], [3, 4]])

    def test_parse_float_values(self):
        m = parse_matrix_text("1.5 2.5\n3.5 4.5")
        self.assertEqual(m.data, [[1.5, 2.5], [3.5, 4.5]])

    def test_parse_empty_raises(self):
        with self.assertRaises(ValueError):
            parse_matrix_text("")
        with self.assertRaises(ValueError):
            parse_matrix_text("   \n   ")

    def test_parse_ragged_rows_raises(self):
        with self.assertRaises(ValueError):
            parse_matrix_text("1 2\n3")

    def test_parse_only_whitespace_lines_skipped(self):
        m = parse_matrix_text("1 2\n\n3 4\n")
        self.assertEqual(m.data, [[1, 2], [3, 4]])


if __name__ == "__main__":
    unittest.main()