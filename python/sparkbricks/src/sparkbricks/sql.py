"""SQL helper functions for interactive use.

Provides convenient wrappers around Spark SQL operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import DataFrame


def sql(query: str, schema: str | None = None, show: bool = True) -> "DataFrame | None":
    """Run SQL query.

    Note: The `schema` parameter here refers to a Databricks namespace
    (catalog.schema_name like "uat_cha_sandbox.erik"), not a table schema.

    Args:
        query: SQL query string
        schema: Default schema (catalog.schema_name) for unqualified table names
        show: If True, display results immediately

    Returns:
        DataFrame or None if no spark session

    Example:
        >>> df = sql("SELECT * FROM my_table LIMIT 10")
        >>> df = sql("SELECT * FROM my_table", schema="catalog.schema", show=False)
    """
    from sparkbricks.connect import get_spark

    spark = get_spark()
    if spark is None:
        print("Error: Spark not connected")
        return None

    if schema:
        spark.sql(f"USE {schema}")

    df = spark.sql(query)
    if show:
        df.show(truncate=False)
    return df


def table(name: str, schema: str | None = None) -> "DataFrame | None":
    """Get table as DataFrame.

    Note: The `schema` parameter here refers to a Databricks namespace
    (catalog.schema_name), not a table schema.

    Args:
        name: Table name (qualified or unqualified)
        schema: Default schema (catalog.schema_name) if name is unqualified

    Returns:
        DataFrame or None if no spark session

    Example:
        >>> df = table("catalog.schema.my_table")
        >>> df = table("my_table", schema="catalog.schema")
    """
    from sparkbricks.connect import get_spark

    spark = get_spark()
    if spark is None:
        print("Error: Spark not connected")
        return None

    if "." not in name and schema:
        name = f"{schema}.{name}"

    return spark.table(name)


def tables(schema: str, pattern: str = "*") -> None:
    """List tables in schema.

    Note: The `schema` parameter here refers to a Databricks namespace
    (catalog.schema_name like "uat_cha_sandbox.erik").

    Args:
        schema: Schema (catalog.schema_name) to list tables from
        pattern: LIKE pattern for filtering

    Example:
        >>> tables("uat_cha_sandbox.myuser")
        >>> tables("uat_cha_sandbox.myuser", pattern="centene*")
    """
    sql(f"SHOW TABLES IN {schema} LIKE '{pattern}'")


def describe(table_name: str, schema: str | None = None) -> None:
    """Describe table schema (columns and types).

    Note: The `schema` parameter here refers to a Databricks namespace
    (catalog.schema_name), not a table schema.

    Args:
        table_name: Table name (qualified or unqualified)
        schema: Default schema (catalog.schema_name) if name is unqualified

    Example:
        >>> describe("catalog.schema.my_table")
        >>> describe("my_table", schema="catalog.schema")
    """
    if "." not in table_name and schema:
        table_name = f"{schema}.{table_name}"
    sql(f"DESCRIBE TABLE {table_name}")


def count(table_name: str, schema: str | None = None) -> int | None:
    """Count rows in table.

    Note: The `schema` parameter here refers to a Databricks namespace
    (catalog.schema_name), not a table schema.

    Args:
        table_name: Table name (qualified or unqualified)
        schema: Default schema (catalog.schema_name) if name is unqualified

    Returns:
        Row count or None if no spark session

    Example:
        >>> cnt = count("catalog.schema.my_table")
        catalog.schema.my_table: 1,234,567 rows
    """
    from sparkbricks.connect import get_spark

    spark = get_spark()
    if spark is None:
        print("Error: Spark not connected")
        return None

    if "." not in table_name and schema:
        table_name = f"{schema}.{table_name}"

    result = spark.sql(f"SELECT COUNT(*) as cnt FROM {table_name}").collect()
    cnt = result[0].cnt
    print(f"{table_name}: {cnt:,} rows")
    return cnt
