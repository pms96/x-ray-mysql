import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Switch } from './ui/switch';
import { ScrollArea } from './ui/scroll-area';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from './ui/accordion';
import { 
    Database, 
    Plus, 
    Trash2, 
    Table2,
    Key,
    Hash,
    ArrowUpDown
} from 'lucide-react';

const DIALECTS = [
    { id: 'postgresql', name: 'PostgreSQL', color: 'text-blue-400' },
    { id: 'mysql', name: 'MySQL', color: 'text-orange-400' },
    { id: 'sqlserver', name: 'SQL Server', color: 'text-red-400' },
    { id: 'bigquery', name: 'BigQuery', color: 'text-yellow-400' },
    { id: 'snowflake', name: 'Snowflake', color: 'text-cyan-400' },
    { id: 'redshift', name: 'Redshift', color: 'text-purple-400' },
    { id: 'athena', name: 'Athena/Presto', color: 'text-pink-400' },
    { id: 'sqlite', name: 'SQLite', color: 'text-green-400' },
];

const INDEX_TYPES = ['B-Tree', 'Hash', 'GIN', 'GiST', 'BRIN', 'Bitmap', 'Clustered', 'Non-Clustered'];

const ConfigPanel = ({
    dialect,
    setDialect,
    schemas,
    setSchemas,
    explainOutput,
    setExplainOutput,
    mode,
    setMode,
    growthSimulation,
    setGrowthSimulation
}) => {
    const [newTableName, setNewTableName] = useState('');
    const [createTableSQL, setCreateTableSQL] = useState('');

    const addTable = () => {
        if (!newTableName.trim()) return;
        
        setSchemas([...schemas, {
            table_name: newTableName,
            columns: [],
            row_count: null,
            indexes: []
        }]);
        setNewTableName('');
    };

    const removeTable = (index) => {
        setSchemas(schemas.filter((_, i) => i !== index));
    };

    const addColumn = (tableIndex) => {
        const updated = [...schemas];
        updated[tableIndex].columns.push({
            name: '',
            type: 'VARCHAR',
            nullable: true,
            primary_key: false,
            foreign_key: null,
            index_type: null,
            cardinality: null
        });
        setSchemas(updated);
    };

    const updateColumn = (tableIndex, colIndex, field, value) => {
        const updated = [...schemas];
        updated[tableIndex].columns[colIndex][field] = value;
        setSchemas(updated);
    };

    const removeColumn = (tableIndex, colIndex) => {
        const updated = [...schemas];
        updated[tableIndex].columns.splice(colIndex, 1);
        setSchemas(updated);
    };

    const updateTableStats = (tableIndex, field, value) => {
        const updated = [...schemas];
        updated[tableIndex][field] = value;
        setSchemas(updated);
    };

    const parseCreateTable = () => {
        if (!createTableSQL.trim()) return;
        
        // Simple parser for CREATE TABLE
        const tableMatch = createTableSQL.match(/CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"']?(\w+)[`"']?/i);
        if (!tableMatch) return;
        
        const tableName = tableMatch[1];
        const columnsMatch = createTableSQL.match(/\(([\s\S]+)\)/);
        if (!columnsMatch) return;
        
        const columnsStr = columnsMatch[1];
        const columnLines = columnsStr.split(',').map(l => l.trim()).filter(l => l && !l.match(/^(PRIMARY|FOREIGN|UNIQUE|INDEX|KEY|CONSTRAINT)/i));
        
        const columns = columnLines.map(line => {
            const parts = line.split(/\s+/);
            const name = parts[0].replace(/[`"']/g, '');
            const type = parts[1] || 'VARCHAR';
            const isPK = line.toUpperCase().includes('PRIMARY KEY');
            const isNotNull = line.toUpperCase().includes('NOT NULL');
            
            return {
                name,
                type: type.toUpperCase(),
                nullable: !isNotNull,
                primary_key: isPK,
                foreign_key: null,
                index_type: isPK ? 'B-Tree' : null,
                cardinality: null
            };
        });
        
        setSchemas([...schemas, {
            table_name: tableName,
            columns,
            row_count: null,
            indexes: []
        }]);
        setCreateTableSQL('');
    };

    return (
        <div className="config-panel h-full" data-testid="config-panel">
            <ScrollArea className="h-full">
                <div className="p-4 space-y-6">
                    {/* Dialect Selector */}
                    <div>
                        <h3 className="section-header flex items-center gap-2">
                            <Database className="w-4 h-4" />
                            SQL Dialect
                        </h3>
                        <div className="grid grid-cols-2 gap-2">
                            {DIALECTS.map((d) => (
                                <button
                                    key={d.id}
                                    onClick={() => setDialect(d.id)}
                                    className={`dialect-item text-left text-sm ${dialect === d.id ? 'active' : ''}`}
                                    data-testid={`dialect-${d.id}`}
                                >
                                    <span className={`w-2 h-2 rounded-full ${d.color} bg-current`} />
                                    {d.name}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Mode Toggles */}
                    <div>
                        <h3 className="section-header">Analysis Mode</h3>
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="mode-beginner" className="text-sm">Beginner Mode</Label>
                                <Switch 
                                    id="mode-beginner"
                                    checked={mode === 'beginner'}
                                    onCheckedChange={(checked) => setMode(checked ? 'beginner' : 'advanced')}
                                    data-testid="mode-beginner-toggle"
                                />
                            </div>
                            <div className="flex items-center justify-between">
                                <Label htmlFor="mode-strict" className="text-sm">Strict Mode</Label>
                                <Switch 
                                    id="mode-strict"
                                    checked={mode === 'strict'}
                                    onCheckedChange={(checked) => setMode(checked ? 'strict' : 'advanced')}
                                    data-testid="mode-strict-toggle"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Growth Simulation */}
                    <div>
                        <h3 className="section-header flex items-center gap-2">
                            <ArrowUpDown className="w-4 h-4" />
                            Growth Simulation
                        </h3>
                        <div className="flex flex-wrap gap-2">
                            {[null, '10x', '100x', '1000x'].map((sim) => (
                                <Button
                                    key={sim || 'none'}
                                    variant={growthSimulation === sim ? 'default' : 'outline'}
                                    size="sm"
                                    className="rounded-sm"
                                    onClick={() => setGrowthSimulation(sim)}
                                    data-testid={`growth-sim-${sim || 'none'}`}
                                >
                                    {sim || 'Current'}
                                </Button>
                            ))}
                        </div>
                    </div>

                    {/* Schema Builder */}
                    <div>
                        <h3 className="section-header flex items-center gap-2">
                            <Table2 className="w-4 h-4" />
                            Table Schemas
                        </h3>
                        
                        <Accordion type="single" collapsible className="space-y-2">
                            {/* Add from CREATE TABLE */}
                            <AccordionItem value="create-table" className="border border-border rounded-sm">
                                <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                                    Paste CREATE TABLE
                                </AccordionTrigger>
                                <AccordionContent className="px-3 pb-3">
                                    <Textarea
                                        value={createTableSQL}
                                        onChange={(e) => setCreateTableSQL(e.target.value)}
                                        placeholder="CREATE TABLE users (id INT PRIMARY KEY, ..."
                                        className="h-24 font-mono text-xs mb-2"
                                        data-testid="create-table-input"
                                    />
                                    <Button 
                                        size="sm" 
                                        onClick={parseCreateTable}
                                        className="w-full rounded-sm"
                                        data-testid="parse-create-table-btn"
                                    >
                                        Parse & Add
                                    </Button>
                                </AccordionContent>
                            </AccordionItem>

                            {/* Manual Add */}
                            <AccordionItem value="manual-add" className="border border-border rounded-sm">
                                <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                                    Add Table Manually
                                </AccordionTrigger>
                                <AccordionContent className="px-3 pb-3">
                                    <div className="flex gap-2">
                                        <Input
                                            value={newTableName}
                                            onChange={(e) => setNewTableName(e.target.value)}
                                            placeholder="Table name"
                                            className="flex-1"
                                            data-testid="new-table-name-input"
                                        />
                                        <Button 
                                            size="icon" 
                                            onClick={addTable}
                                            className="rounded-sm"
                                            data-testid="add-table-btn"
                                        >
                                            <Plus className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </AccordionContent>
                            </AccordionItem>

                            {/* Existing Tables */}
                            {schemas.map((table, tableIndex) => (
                                <AccordionItem 
                                    key={tableIndex} 
                                    value={`table-${tableIndex}`}
                                    className="border border-border rounded-sm"
                                >
                                    <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                                        <div className="flex items-center gap-2">
                                            <Table2 className="w-4 h-4 text-primary" />
                                            <span className="font-mono">{table.table_name}</span>
                                            <span className="text-xs text-muted-foreground">
                                                ({table.columns.length} cols)
                                            </span>
                                        </div>
                                    </AccordionTrigger>
                                    <AccordionContent className="px-3 pb-3 space-y-3">
                                        {/* Table Stats */}
                                        <div className="grid grid-cols-2 gap-2">
                                            <div>
                                                <Label className="text-xs">Row Count</Label>
                                                <Input
                                                    type="number"
                                                    value={table.row_count || ''}
                                                    onChange={(e) => updateTableStats(tableIndex, 'row_count', parseInt(e.target.value) || null)}
                                                    placeholder="e.g. 1000000"
                                                    className="h-8 text-xs"
                                                />
                                            </div>
                                            <div>
                                                <Label className="text-xs">Size (MB)</Label>
                                                <Input
                                                    type="number"
                                                    value={table.size_mb || ''}
                                                    onChange={(e) => updateTableStats(tableIndex, 'size_mb', parseFloat(e.target.value) || null)}
                                                    placeholder="e.g. 500"
                                                    className="h-8 text-xs"
                                                />
                                            </div>
                                        </div>

                                        {/* Columns */}
                                        <div className="space-y-2">
                                            {table.columns.map((col, colIndex) => (
                                                <div key={colIndex} className="schema-card">
                                                    <div className="grid grid-cols-2 gap-2 mb-2">
                                                        <Input
                                                            value={col.name}
                                                            onChange={(e) => updateColumn(tableIndex, colIndex, 'name', e.target.value)}
                                                            placeholder="Column name"
                                                            className="h-7 text-xs font-mono"
                                                        />
                                                        <Input
                                                            value={col.type}
                                                            onChange={(e) => updateColumn(tableIndex, colIndex, 'type', e.target.value)}
                                                            placeholder="Type"
                                                            className="h-7 text-xs font-mono"
                                                        />
                                                    </div>
                                                    <div className="flex items-center gap-3 text-xs">
                                                        <label className="flex items-center gap-1">
                                                            <input
                                                                type="checkbox"
                                                                checked={col.primary_key}
                                                                onChange={(e) => updateColumn(tableIndex, colIndex, 'primary_key', e.target.checked)}
                                                            />
                                                            <Key className="w-3 h-3" /> PK
                                                        </label>
                                                        <label className="flex items-center gap-1">
                                                            <input
                                                                type="checkbox"
                                                                checked={col.index_type === 'B-Tree'}
                                                                onChange={(e) => updateColumn(tableIndex, colIndex, 'index_type', e.target.checked ? 'B-Tree' : null)}
                                                            />
                                                            <Hash className="w-3 h-3" /> Index
                                                        </label>
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-6 w-6 ml-auto"
                                                            onClick={() => removeColumn(tableIndex, colIndex)}
                                                        >
                                                            <Trash2 className="w-3 h-3 text-destructive" />
                                                        </Button>
                                                    </div>
                                                </div>
                                            ))}
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="w-full rounded-sm"
                                                onClick={() => addColumn(tableIndex)}
                                            >
                                                <Plus className="w-3 h-3 mr-1" /> Add Column
                                            </Button>
                                        </div>

                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="w-full text-destructive hover:text-destructive"
                                            onClick={() => removeTable(tableIndex)}
                                        >
                                            <Trash2 className="w-3 h-3 mr-1" /> Remove Table
                                        </Button>
                                    </AccordionContent>
                                </AccordionItem>
                            ))}
                        </Accordion>
                    </div>

                    {/* EXPLAIN Output */}
                    <div>
                        <h3 className="section-header">EXPLAIN / EXPLAIN ANALYZE</h3>
                        <Textarea
                            value={explainOutput}
                            onChange={(e) => setExplainOutput(e.target.value)}
                            placeholder="Paste your EXPLAIN output here for detailed analysis..."
                            className="h-32 font-mono text-xs"
                            data-testid="explain-output-input"
                        />
                    </div>
                </div>
            </ScrollArea>
        </div>
    );
};

export default ConfigPanel;
